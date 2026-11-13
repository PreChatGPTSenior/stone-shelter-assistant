"""Opt-in disposable end-to-end run for the twenty-question challenge suite."""

import hashlib
import json
import os
import subprocess
from dataclasses import asdict, is_dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any, cast

import pytest
from httpx import ASGITransport, AsyncClient
from tests.evaluation.run_identity import (
    EvaluationRunIdentity,
    comparison_id_from_environment,
    first_run_number_from_environment,
)

import stone_shelter_assistant.assistant.workflow as workflow_module
import stone_shelter_assistant.dependencies as dependencies
from stone_shelter_assistant.app import create_app
from stone_shelter_assistant.core.settings import (
    OllamaEmbeddingSettings,
    OpenRouterSettings,
)

ROOT = Path(__file__).parents[2]
SUITE = ROOT / "tests/fixtures/agent-eval/questions-challenge-20"
MANIFEST = SUITE / "scenarios.json"


def _selected_cases(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    requested = os.getenv("EVALUATION_CASE_IDS")
    cases = manifest["scenarios"]
    if not requested:
        return cast(list[dict[str, Any]], cases)
    ids = [part.strip() for part in requested.split(",") if part.strip()]
    if not ids or len(ids) != len(set(ids)):
        raise ValueError("EVALUATION_CASE_IDS must be a unique comma-separated list")
    by_id = {case["id"]: case for case in cases}
    unknown = set(ids) - set(by_id)
    if unknown:
        raise ValueError(f"Unknown challenge case IDs: {sorted(unknown)}")
    return [by_id[case_id] for case_id in ids]


def _code_hash() -> tuple[str, dict[str, str]]:
    tracked = subprocess.run(
        ["git", "ls-files", "-z"], cwd=ROOT, check=True, capture_output=True
    ).stdout.split(b"\0")
    paths = {
        (ROOT / entry.decode()).resolve()
        for entry in tracked
        if entry
        and not Path(entry.decode()).name.startswith(".env")
        and (
            entry.decode().startswith("src/stone_shelter_assistant/")
            or entry.decode().startswith("tests/")
        )
        and (ROOT / entry.decode()).is_file()
    }
    paths.add(Path(__file__).resolve())
    hashes = {}
    digest = hashlib.sha256()
    for path in sorted(paths):
        relative = path.relative_to(ROOT).as_posix()
        content = path.read_bytes()
        hashes[relative] = hashlib.sha256(content).hexdigest()
        digest.update(relative.encode())
        digest.update(content)
    return digest.hexdigest(), hashes


def _json_value(value: Any) -> Any:
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        items = sorted(value, key=str) if isinstance(value, (set, frozenset)) else value
        return [_json_value(item) for item in items]
    if hasattr(value, "value"):
        return value.value
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _persist(path: Path, result: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def _capture_http_response(record: dict[str, Any], response: Any) -> bool:
    """Archive an HTTP result without letting a non-JSON failure mask its status."""
    record["http_status"] = response.status_code
    if not response.is_success:
        record["technical_error"] = f"HTTP {response.status_code}"
        try:
            record["response"] = response.json()
        except ValueError:
            record["response_body"] = response.text[:4000]
        return False
    try:
        payload = response.json()
        record["response"] = payload
    except ValueError as error:
        record["technical_error"] = type(error).__name__
        record["error_message"] = str(error)[:500]
        record["response_body"] = response.text[:4000]
        return False
    if isinstance(payload, dict):
        record["trace_id"] = payload.get("trace_id")
        evaluation_run = payload.get("evaluation_run")
        if isinstance(evaluation_run, dict):
            record["configuration_id"] = evaluation_run.get("configuration_id")
    return True


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_QUESTIONS_CHALLENGE_20") != "1",
    reason="Explicit disposable-store and model-run opt-in required",
)
async def test_questions_challenge_20_live(
    migrated_database: Any,
    typesense_settings: Any,
    qdrant_settings: Any,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest = json.loads(MANIFEST.read_text())
    cases = _selected_cases(manifest)
    parsing_model = os.getenv("LUNA_MODEL_ID", "openai/gpt-6-luna")
    free_model = os.getenv("FREE_MODEL_ID", "nvidia/nemotron-3.5-super-vl:free")
    embedding_model = os.getenv("CHALLENGE_EMBEDDING_MODEL", "qwen3-embedding:0.6b")
    embedding_dimension = int(os.getenv("CHALLENGE_EMBEDDING_DIMENSION", "1024"))
    openrouter = OpenRouterSettings().model_copy(
        update={
            "model": free_model,
            "selection_model": free_model,
            "parsing_model": parsing_model,
            "evaluation_model": parsing_model,
            "answer_model": free_model,
            "evaluation_max_tokens": 8192,
            "evaluation_reasoning_effort": "medium",
        }
    )
    ollama = OllamaEmbeddingSettings().model_copy(
        update={
            "embedding_model": embedding_model,
            "embedding_dimension": embedding_dimension,
        }
    )
    monkeypatch.setattr("stone_shelter_assistant.app.DatabaseSettings", lambda: migrated_database)
    monkeypatch.setattr("stone_shelter_assistant.app.TypesenseSettings", lambda: typesense_settings)
    monkeypatch.setattr("stone_shelter_assistant.app.QdrantSettings", lambda: qdrant_settings)
    monkeypatch.setattr("stone_shelter_assistant.app.OllamaEmbeddingSettings", lambda: ollama)
    monkeypatch.setattr(dependencies, "OpenRouterSettings", lambda: openrouter)

    captured_states: list[dict[str, Any]] = []
    original_build_graph = workflow_module.build_graph

    def build_capture_graph() -> Any:
        graph = original_build_graph()

        class CapturingGraph:
            async def ainvoke(self, *args: Any, **kwargs: Any) -> Any:
                state = await graph.ainvoke(*args, **kwargs)
                captured_states.append(_json_value(state))
                return state

        return CapturingGraph()

    monkeypatch.setattr(workflow_module, "build_graph", build_capture_graph)

    files = {MANIFEST, *[ROOT / stone["fixture"] for stone in manifest["stones"]]}
    files.update(
        path
        for directory in (
            ROOT / "fixtures/knowledge/stone-encyclopedias",
            ROOT / "fixtures/knowledge/type-compatibility",
            ROOT / "fixtures/knowledge/grounding",
        )
        for path in directory.rglob("*")
        if path.is_file() and path.name != "README.md"
    )
    fixture_hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(files)
    }
    source_hash, source_hashes = _code_hash()
    now = datetime.now(UTC)
    comparison_id = comparison_id_from_environment(now)
    run_number = first_run_number_from_environment()
    identity = EvaluationRunIdentity.create(comparison_id, run_number)
    runs_dir = SUITE / "runs"
    existing_runs = list(
        runs_dir.glob(f"{comparison_id}-r{run_number:02d}-*-challenge20.json")
    )
    if existing_runs:
        raise ValueError(
            f"Run {run_number} already exists in comparison {comparison_id}; choose a new run number"
        )
    run_path = runs_dir / (
        f"{comparison_id}-r{run_number:02d}-{now:%Y%m%dT%H%M%S%fZ}-challenge20.json"
    )
    run_path.parent.mkdir(exist_ok=True)
    result: dict[str, Any] = {
        "mode": "questions-challenge-20-live",
        **identity.as_metadata(),
        "session_id": identity.session_id,
        "configuration_id": None,
        "suite_id": manifest["suite_id"],
        "started_at": now.isoformat(),
        "status": "running",
        "selected_case_ids": [case["id"] for case in cases],
        "models": {
            "parsing": parsing_model,
            "grounding_and_candidate_evidence": parsing_model,
            "selection": free_model,
            "answer": free_model,
            "embedding": embedding_model,
        },
        "settings": {
            "embedding_dimension": embedding_dimension,
            "evaluation_max_tokens": 8192,
            "evaluation_reasoning_effort": "medium",
            "model_retries": 0,
            "semantic_judge": "disabled",
            "telemetry_capture": "local_graph_state_only",
        },
        "fixture_hashes": fixture_hashes,
        "source_hash": source_hash,
        "source_hashes": source_hashes,
        "records": [],
    }
    _persist(run_path, result)

    app = create_app()
    failures = []
    async with app.router.lifespan_context(app):
        sample_vector = await app.state.embeddings.aembed_query("challenge fixture vector check")
        if len(sample_vector) != embedding_dimension:
            raise ValueError(
                f"Ollama returned {len(sample_vector)} dimensions; configured {embedding_dimension}"
            )
        async with AsyncClient(
            transport=ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as http:
            for endpoint in (
                "/api/v1/stones/reload",
                "/api/v1/knowledge/encyclopedia/reindex",
                "/api/v1/knowledge/compatibility/reindex",
                "/api/v1/knowledge/grounding/reload",
            ):
                response = await http.post(endpoint)
                if not response.is_success:
                    result["setup_error"] = {"endpoint": endpoint, "body": response.text}
                    result["status"] = "setup_failed"
                    _persist(run_path, result)
                    pytest.fail(
                        f"Disposable fixture preparation failed at {endpoint}: {response.text}"
                    )

            for case in cases:
                case_id = case["id"]
                captured_states.clear()
                record: dict[str, Any] = {
                    "case_id": case_id,
                    **identity.as_metadata(),
                    "session_id": identity.session_id,
                    "question": case["question"],
                    "expected": case.get("expected", {}),
                    "request_models": result["models"],
                }
                started = monotonic()
                try:
                    response = await http.post(
                        "/api/v1/questions",
                        headers={"X-Session-ID": identity.session_id},
                        json={
                            "question": case["question"],
                            "model_id": free_model,
                            "parsing_model_id": parsing_model,
                            "evaluation_model_id": parsing_model,
                            "selection_model_id": free_model,
                            "answer_model_id": free_model,
                            "evaluation_max_tokens": 8192,
                            "evaluation_reasoning_effort": "medium",
                            "eval_case_id": case_id,
                            "fixture_version": manifest["suite_id"],
                            "comparison_id": comparison_id,
                            "run_number": run_number,
                            "source_hash": source_hash,
                        },
                    )
                    record["graph_state"] = captured_states[-1] if captured_states else None
                    record["graph_capture_status"] = (
                        "captured" if captured_states else "missing_after_error"
                    )
                    if not _capture_http_response(record, response):
                        failures.append(case_id)
                    elif result["configuration_id"] is None:
                        result["configuration_id"] = record.get("configuration_id")
                except Exception as error:
                    record["technical_error"] = type(error).__name__
                    record["error_message"] = str(error)
                    record["graph_state"] = captured_states[-1] if captured_states else None
                    record["graph_capture_status"] = (
                        "captured" if captured_states else "missing_after_error"
                    )
                    failures.append(case_id)
                record["elapsed_seconds"] = round(monotonic() - started, 3)
                result["records"].append(record)
                _persist(run_path, result)

    result["status"] = "complete_with_failures" if failures else "complete"
    result["failed_case_ids"] = failures
    result["completed_at"] = datetime.now(UTC).isoformat()
    _persist(run_path, result)
    assert not failures, f"Some scenario requests failed; archived at {run_path}"
