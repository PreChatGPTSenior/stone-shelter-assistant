"""Opt-in RAGAS scoring of saved Q01–Q20 scenario runs.

Requires RUN_SAVED_RUN_RAGAS=1, either SAVED_RAGAS_RESULT_PATH or
SAVED_RAGAS_SESSION_ID, and OPENROUTER_RAGAS_MODEL. It scores archived final
answers and sources only; it never runs the workflow or asserts score thresholds.
"""

import hashlib
import json
import os
import re
from datetime import UTC, datetime
from importlib.metadata import version as package_version
from pathlib import Path
from typing import Any

import pytest

pytest.importorskip("ragas", reason="Install the eval dependency group for RAGAS")

ROOT = Path(__file__).resolve().parents[2]


def _select_sources() -> list[Path]:
    result_path = os.getenv("SAVED_RAGAS_RESULT_PATH")
    session_id = os.getenv("SAVED_RAGAS_SESSION_ID")
    if bool(result_path) == bool(session_id):
        raise ValueError("Set exactly one of SAVED_RAGAS_RESULT_PATH or SAVED_RAGAS_SESSION_ID")
    if result_path:
        return [Path(result_path).resolve()]
    if session_id is None or not re.fullmatch(r"[A-Za-z0-9._-]+", session_id):
        raise ValueError(
            "SAVED_RAGAS_SESSION_ID may contain only letters, digits, dot, underscore, and hyphen"
        )
    return [
        ROOT / "test-evaluation-results" / f"Q{index:02d}" / session_id / "result.json"
        for index in range(1, 21)
    ]


def _load_case(source: Path) -> tuple[bytes, dict[str, Any], str, list[str]]:
    source_bytes = source.read_bytes()
    result = json.loads(source_bytes)
    graph_state = result.get("graph_state")
    graph_result = graph_state.get("result") if isinstance(graph_state, dict) else None
    if (
        result.get("status") != "completed"
        or not isinstance(result.get("question"), str)
        or not isinstance(result.get("expected"), dict)
        or not isinstance(graph_result, dict)
        or not isinstance(graph_result.get("answer"), str)
        or not isinstance(graph_result.get("sources"), dict)
    ):
        raise ValueError(f"Saved result lacks a completed current answer and sources: {source}")
    case_id = result.get("case_id")
    if not isinstance(case_id, str) or case_id != source.parent.parent.name:
        raise ValueError(f"Saved result case ID does not match its archive directory: {source}")
    sources = graph_result["sources"]
    contexts = [
        json.dumps({"source_ref": key, **value}, ensure_ascii=False, sort_keys=True)
        for key, value in sources.items()
        if isinstance(key, str) and isinstance(value, dict)
    ]
    if len(contexts) != len(sources):
        raise ValueError(f"Saved answer has invalid final source contexts: {source}")
    return source_bytes, result, graph_result["answer"], contexts


def _load_references(path: Path, cases: list[dict[str, Any]]) -> tuple[bytes, dict[str, str]]:
    source_bytes = path.read_bytes()

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        parsed: dict[str, Any] = {}
        for key, value in pairs:
            if key in parsed:
                raise ValueError(f"Duplicate reference JSON key: {key}")
            parsed[key] = value
        return parsed

    payload = json.loads(source_bytes, object_pairs_hook=reject_duplicate_keys)
    if not isinstance(payload, dict) or set(payload) != {"references"}:
        raise ValueError("RAGAS references file must contain only a 'references' array")
    records = payload["references"]
    if not isinstance(records, list):
        raise ValueError("RAGAS references must be an array of case records")

    available: dict[str, tuple[str, str]] = {}
    for index, record in enumerate(records):
        if (
            not isinstance(record, dict)
            or set(record) != {"case_id", "question", "reference"}
            or not isinstance(record["case_id"], str)
            or not re.fullmatch(r"Q\d{2}", record["case_id"])
            or not isinstance(record["question"], str)
            or not isinstance(record["reference"], str)
            or not record["reference"].strip()
        ):
            raise ValueError(f"Malformed RAGAS reference record at index {index}")
        case_id = record["case_id"]
        if case_id in available:
            raise ValueError(f"Duplicate RAGAS reference case ID: {case_id}")
        available[case_id] = (record["question"], record["reference"])

    selected: dict[str, str] = {}
    for case in cases:
        case_id = case["result"]["case_id"]
        matching = available.get(case_id)
        if matching is None:
            continue
        question, reference = matching
        if question != case["result"]["question"]:
            raise ValueError(f"RAGAS reference question does not exactly match {case_id}")
        selected[case_id] = reference
    return source_bytes, selected


def _write_checkpoint(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.mark.skipif(
    os.getenv("RUN_SAVED_RUN_RAGAS") != "1"
    or not (os.getenv("SAVED_RAGAS_RESULT_PATH") or os.getenv("SAVED_RAGAS_SESSION_ID")),
    reason="Explicit paid RAGAS opt-in and a saved result path or session ID are required",
)
@pytest.mark.asyncio
async def test_saved_run_ragas() -> None:
    from dotenv import load_dotenv
    from openai import AsyncOpenAI
    from ragas.embeddings.base import modern_embedding_factory
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    from stone_shelter_assistant.core.settings import OpenRouterSettings

    load_dotenv(ROOT / ".env", override=False)
    model_id = os.getenv("OPENROUTER_RAGAS_MODEL")
    if not model_id:
        raise ValueError("Set OPENROUTER_RAGAS_MODEL explicitly before enabling paid RAGAS")
    embedding_model = os.getenv("OPENROUTER_RAGAS_EMBEDDING_MODEL", "openai/text-embedding-3-small")
    api_key = OpenRouterSettings().api_key.get_secret_value()
    if not api_key:
        raise ValueError("Set OPENROUTER_API_KEY in the process environment or project .env")

    sources = _select_sources()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    prepared: list[dict[str, Any]] = []
    # Preflight every case and output path before the first evaluator request.
    for source in sources:
        source_bytes, result, answer, contexts = _load_case(source)
        session_id = os.getenv("SAVED_RAGAS_SESSION_ID")
        if session_id and result.get("session_id") != session_id:
            raise ValueError(f"Saved result has a different session ID: {source}")
        report_path = source.with_name(f"{source.stem}-ragas-{timestamp}.json")
        if report_path.exists():
            raise FileExistsError(f"Refusing to overwrite an evaluation report: {report_path}")
        prepared.append(
            {
                "source": source,
                "source_bytes": source_bytes,
                "result": result,
                "answer": answer,
                "contexts": contexts,
                "report_path": report_path,
            }
        )

    reference_path_value = os.getenv("SAVED_RAGAS_REFERENCES_PATH")
    reference_source: dict[str, str] | None = None
    references: dict[str, str] = {}
    if reference_path_value:
        reference_path = Path(reference_path_value).resolve()
        reference_bytes, references = _load_references(reference_path, prepared)
        reference_source = {
            "path": str(reference_path),
            "sha256": hashlib.sha256(reference_bytes).hexdigest(),
        }
    for case in prepared:
        case["reference"] = references.get(case["result"]["case_id"])

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        max_retries=0,
        timeout=120.0,
    )
    llm = llm_factory(model_id, provider="openai", client=client)
    embeddings = modern_embedding_factory("openai", model=embedding_model, client=client)
    metrics = {
        "faithfulness": Faithfulness(llm=llm),
        "response_relevancy": AnswerRelevancy(llm=llm, embeddings=embeddings),
        "context_precision": ContextPrecision(llm=llm),
        "context_recall": ContextRecall(llm=llm),
    }

    execution_failures: list[str] = []
    try:
        for case in prepared:
            source = case["source"]
            result = case["result"]
            report: dict[str, Any] = {
                "status": "prepared",
                "evaluated_at": datetime.now(UTC).isoformat(),
                "source_result": str(source),
                "source_result_sha256": hashlib.sha256(case["source_bytes"]).hexdigest(),
                "source_trace_id": result.get("trace_id"),
                "case_id": result["case_id"],
                "judge_settings": {
                    "metric": "RAGAS collections API",
                    "ragas_version": package_version("ragas"),
                    "model": model_id,
                    "embedding_model": embedding_model,
                    "thresholds": None,
                },
                "reference": case["reference"],
                "reference_status": "available" if case["reference"] else "unavailable",
                "reference_source": reference_source,
                "reference_unavailable_reason": None
                if case["reference"]
                else (
                    "No separately curated factual reference answer is available. Scenario required/"
                    "forbidden assertions are evaluation criteria, not canonical answer text."
                ),
                "captured_question": result["question"],
                "captured_answer": case["answer"],
                "captured_contexts": case["contexts"],
                "metric_results": {},
            }
            _write_checkpoint(case["report_path"], report)
            metric_inputs = {
                "faithfulness": {
                    "user_input": result["question"],
                    "response": case["answer"],
                    "retrieved_contexts": case["contexts"],
                },
                "response_relevancy": {
                    "user_input": result["question"],
                    "response": case["answer"],
                },
            }
            if case["reference"]:
                metric_inputs["context_precision"] = {
                    "user_input": result["question"],
                    "retrieved_contexts": case["contexts"],
                    "reference": case["reference"],
                }
                metric_inputs["context_recall"] = {
                    "user_input": result["question"],
                    "retrieved_contexts": case["contexts"],
                    "reference": case["reference"],
                }
            failures = []
            for name, metric in metrics.items():
                unavailable_reason = None
                if name in {"context_precision", "context_recall"} and not case["reference"]:
                    unavailable_reason = report["reference_unavailable_reason"]
                elif name == "faithfulness" and not case["contexts"]:
                    unavailable_reason = (
                        "The saved answer has no retrieved contexts to check against."
                    )
                if unavailable_reason:
                    report["metric_results"][name] = {
                        "status": "unavailable",
                        "reason": unavailable_reason,
                    }
                    _write_checkpoint(case["report_path"], report)
                    continue
                try:
                    scored = await metric.ascore(**metric_inputs[name])
                    report["metric_results"][name] = {"status": "completed", "value": scored.value}
                except Exception as error:
                    failures.append(name)
                    execution_failures.append(f"{case['result']['case_id']}:{name}")
                    report["metric_results"][name] = {
                        "status": "failed",
                        "error_type": type(error).__name__,
                    }
                finally:
                    report["evaluated_at"] = datetime.now(UTC).isoformat()
                    report["status"] = "in_progress"
                    _write_checkpoint(case["report_path"], report)
            report["status"] = "completed_with_metric_failures" if failures else "completed"
            if failures:
                report["failed_metrics"] = failures
            _write_checkpoint(case["report_path"], report)
    finally:
        await client.close()
    if execution_failures:
        raise RuntimeError("RAGAS metric execution failed for " + ", ".join(execution_failures))
