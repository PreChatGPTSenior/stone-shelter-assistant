"""Opt-in paid JevEval of saved full-run final answers.

Requires RUN_SAVED_RUN_JEV_EVALUATION=1, either SAVED_JEV_RESULT_PATH or
SAVED_JEV_SESSION_ID, and an explicit JEV_MODEL. Session mode preflights all 20
archives before evaluating any answer. It never reruns the workflow.
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

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "YES")
pytest.importorskip("deepeval", reason="Install the eval dependency group for DeepEval")
from deepeval.metrics import JevEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from dotenv import load_dotenv

from stone_shelter_assistant.core.settings import OpenRouterSettings
from tests.evaluation.support.jev_saved_run import (
    SCORE_THRESHOLD_TOLERANCE,
    JEv_ENDPOINT,
    OpenRouterJevModel,
    criterion_gates_pass,
    criterion_questions,
    sanitize_payload,
    score_meets_threshold,
)

ROOT = Path(__file__).resolve().parents[2]


def _model_slug(model: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", model.casefold()).strip("-")
    if not slug:
        raise ValueError("JEV_MODEL must produce a non-empty filename slug")
    return slug[:80]


def _load_saved_case(
    source: Path,
) -> tuple[bytes, dict[str, Any], bytes, dict[str, Any]]:
    source_bytes = source.read_bytes()
    observation_path = source.with_name("observations.json")
    observation_bytes = observation_path.read_bytes()
    result = json.loads(source_bytes)
    observations = json.loads(observation_bytes)
    graph_state = result.get("graph_state")
    graph_result = graph_state.get("result") if isinstance(graph_state, dict) else None
    response = result.get("response")
    if (
        result.get("status") != "completed"
        or not isinstance(result.get("question"), str)
        or not isinstance(result.get("expected"), dict)
        or not isinstance(graph_result, dict)
        or not isinstance(response, dict)
        or response.get("answer") != graph_result.get("answer")
        or not isinstance(graph_result.get("answer"), str)
        or not isinstance(graph_result.get("sources"), dict)
    ):
        raise ValueError(f"Saved result lacks a matching current answer and sources: {source}")
    entries = observations.get("observations")
    if not isinstance(entries, list):
        raise ValueError(f"Saved observations archive has no observations list: {observation_path}")
    return source_bytes, result, observation_bytes, observations


def _select_sources() -> list[Path]:
    result_path = os.getenv("SAVED_JEV_RESULT_PATH")
    session_id = os.getenv("SAVED_JEV_SESSION_ID")
    if bool(result_path) == bool(session_id):
        raise ValueError("Set exactly one of SAVED_JEV_RESULT_PATH or SAVED_JEV_SESSION_ID")
    if result_path:
        return [Path(result_path).resolve()]
    if session_id is None or not re.fullmatch(r"[A-Za-z0-9._-]+", session_id):
        raise ValueError(
            "SAVED_JEV_SESSION_ID may contain only letters, digits, dot, underscore, and hyphen"
        )
    paths = [
        ROOT / "test-evaluation-results" / f"Q{index:02d}" / session_id / "result.json"
        for index in range(1, 21)
    ]
    for index, path in enumerate(paths, start=1):
        if not path.is_file():
            raise FileNotFoundError(f"Missing Q{index:02d} result archive: {path}")
    return paths


def _workflow_context(result: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Return only factual fields present in the immutable saved workflow state."""
    graph_state = result["graph_state"]
    graph_result = graph_state["result"]
    available = {
        "assessment": graph_state.get("assessment"),
        "assessment_status": graph_state.get("assessment_status"),
        "candidate_decisions": graph_result.get("candidate_decisions"),
        "verified_statuses": graph_result.get("verified_statuses"),
    }
    missing = [name for name, value in available.items() if value is None]
    return ({name: value for name, value in available.items() if value is not None}, missing)


def _validate_batch_identity(source: Path, result: dict[str, Any], session_id: str) -> None:
    if result.get("session_id") != session_id:
        raise ValueError(f"Saved result has a different session ID: {source}")
    if result.get("case_id") != source.parent.parent.name:
        raise ValueError(f"Saved result case ID does not match its archive directory: {source}")


def _write(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


@pytest.mark.skipif(
    os.getenv("RUN_SAVED_RUN_JEV_EVALUATION") != "1"
    or not (os.getenv("SAVED_JEV_RESULT_PATH") or os.getenv("SAVED_JEV_SESSION_ID")),
    reason="Explicit paid Jev opt-in and a saved result path or session ID are required",
)
@pytest.mark.asyncio
async def test_saved_run_answer_jev() -> None:
    load_dotenv(ROOT / ".env", override=False)
    model_id = os.getenv("JEV_MODEL")
    if not model_id:
        raise ValueError("Set JEV_MODEL explicitly before enabling paid Jev evaluation")
    model_slug = _model_slug(model_id)
    api_key = OpenRouterSettings().api_key.get_secret_value()
    if not api_key:
        raise ValueError("Set OPENROUTER_API_KEY in the process environment or project .env")

    sources = _select_sources()
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    prepared: list[dict[str, Any]] = []
    # Load and validate every archive and destination before the first paid request.
    for source in sources:
        source_bytes, result, observation_bytes, _ = _load_saved_case(source)
        selected_session = os.getenv("SAVED_JEV_SESSION_ID")
        if selected_session:
            _validate_batch_identity(source, result, selected_session)
        case_id = result.get("case_id")
        if not isinstance(case_id, str):
            raise ValueError(f"Saved result has no valid case ID: {source}")
        if os.getenv("SAVED_JEV_SESSION_ID") and case_id != source.parent.parent.name:
            raise ValueError(f"Saved result case ID does not match its archive directory: {source}")
        questions, criteria, unmeasured = criterion_questions(case_id, result["expected"])
        report_path = source.with_name(f"{source.stem}-jev-{model_slug}-{timestamp}.json")
        if report_path.exists():
            raise FileExistsError(f"Refusing to overwrite an evaluation report: {report_path}")
        workflow_context, missing_context_fields = _workflow_context(result)
        final_sources = result["graph_state"]["result"]["sources"]
        context = {
            "scope": {
                "archived_workflow_context": "factual context from saved result fields only",
                "final_answer": "the only text scored against reviewed answer criteria",
            },
            "final_answer_sources": final_sources,
            "archived_workflow_context": workflow_context,
            "archived_workflow_context_missing_fields": missing_context_fields,
        }
        prepared.append(
            {
                "source": source,
                "source_bytes": source_bytes,
                "observation_bytes": observation_bytes,
                "result": result,
                "case_id": case_id,
                "answer": result["graph_state"]["result"]["answer"],
                "final_sources": final_sources,
                "questions": questions,
                "criteria": criteria,
                "unmeasured": unmeasured,
                "context": context,
                "report_path": report_path,
            }
        )

    for case in prepared:
        source = case["source"]
        result = case["result"]
        answer = case["answer"]
        final_sources = case["final_sources"]
        criteria = case["criteria"]
        unmeasured = case["unmeasured"]
        context = case["context"]
        report_path = case["report_path"]
        test_case = LLMTestCase(
            input=result["question"],
            actual_output=answer,
            retrieval_context=[json.dumps(context, ensure_ascii=False, sort_keys=True)],
        )
        # Jev uses its own explicitly selected System One model adapter, independent of GEval.
        metric_model = OpenRouterJevModel(model_id, api_key)
        metric = JevEval(
            name="saved_scenario_answer_criteria",
            evaluation_params=[
                SingleTurnParams.INPUT,
                SingleTurnParams.ACTUAL_OUTPUT,
                SingleTurnParams.RETRIEVAL_CONTEXT,
            ],
            questions=case["questions"],
            system_one_model=metric_model,
            threshold=0.8,
            include_reason=True,
            async_mode=True,
        )
        run: dict[str, Any] = {
            "status": "prepared",
            "evaluated_at": datetime.now(UTC).isoformat(),
            "source_result": str(source),
            "source_result_sha256": hashlib.sha256(case["source_bytes"]).hexdigest(),
            "source_observations": str(source.with_name("observations.json")),
            "source_observations_sha256": hashlib.sha256(case["observation_bytes"]).hexdigest(),
            "source_trace_id": result.get("trace_id"),
            "case_id": case["case_id"],
            "judge_settings": {
                "metric": "DeepEval JevEval",
                "deepeval_version": package_version("deepeval"),
                "endpoint": JEv_ENDPOINT,
                "model_requested": model_id,
                "threshold": 0.8,
                "threshold_calibrated": False,
                "max_retries": 0,
                "request_timeout_seconds": 120,
            },
            "criterion_questions": criteria,
            "unmeasured_criteria": unmeasured,
            "captured_input": result["question"],
            "captured_answer": answer,
            "captured_sources": final_sources,
            "archived_workflow_context": context["archived_workflow_context"],
            "archived_workflow_context_missing_fields": context[
                "archived_workflow_context_missing_fields"
            ],
            "judge_context": context,
            "request_sha256": None,
            "response_sha256": None,
            "judge_request": None,
            "judge_response": None,
            "criterion_results": [],
        }
        _write(report_path, run)
        try:
            await metric.a_measure(test_case, _show_indicator=False)
            if metric.score is None:
                raise RuntimeError("JevEval completed without a score")
            if metric_model.last_request is None or metric_model.last_safe_response is None:
                raise RuntimeError("JevEval completed without a recorded request and response")
            run.update(
                status="completed",
                model_reported=metric_model.last_safe_response.get("model"),
                request_sha256=hashlib.sha256(
                    json.dumps(
                        metric_model.last_request, ensure_ascii=False, sort_keys=True
                    ).encode()
                ).hexdigest(),
                response_sha256=metric_model.last_response_sha256,
                judge_request=sanitize_payload(metric_model.last_request, api_key),
                judge_response=metric_model.last_safe_response,
                jev_usage=metric_model.last_usage,
                score=metric.score,
                metric_success=metric.success,
                score_threshold_passed=score_meets_threshold(metric.score, 0.8),
                threshold_comparison={
                    "raw_score": metric.score,
                    "threshold": 0.8,
                    "absolute_tolerance": SCORE_THRESHOLD_TOLERANCE,
                },
                confidence=metric.confidence,
                reason=metric.reason,
                criterion_results=[],
                unmeasured_criteria=unmeasured,
                evaluation_cost=metric.evaluation_cost,
                input_tokens=metric.input_tokens,
                output_tokens=metric.output_tokens,
            )
            score_breakdown = metric.score_breakdown or []
            gates_passed, gate_results = criterion_gates_pass(criteria, score_breakdown)
            gate_results_by_id = {gate["id"]: gate for gate in gate_results}
            run["criterion_results"] = [
                {
                    **criterion,
                    **outcome,
                    "applicability_status": (
                        "applicable" if outcome["applicable"] else "not_applicable"
                    ),
                    **(
                        {"gate_result": gate_results_by_id[criterion["id"]]}
                        if criterion["id"] in gate_results_by_id
                        else {}
                    ),
                }
                for criterion, outcome in zip(criteria, score_breakdown, strict=True)
            ]
            run.update(
                required_gates_passed=gates_passed,
                required_gate_results=gate_results,
                success=run["score_threshold_passed"] and gates_passed,
            )
            _write(report_path, run)
        except Exception as error:
            run.update(
                status="technical_error",
                error_type=type(error).__name__,
                diagnostic=sanitize_payload(str(error), api_key)[:400],
                judge_request=(
                    sanitize_payload(metric_model.last_request, api_key)
                    if metric_model.last_request is not None
                    else None
                ),
                judge_response=metric_model.last_safe_response,
                response_sha256=metric_model.last_response_sha256,
                jev_usage=metric_model.last_usage,
            )
            _write(report_path, run)
            raise RuntimeError(
                f"Saved-run Jev evaluation stopped; partial report: {report_path}"
            ) from error
        print(f"Saved Jev result: {report_path}")
