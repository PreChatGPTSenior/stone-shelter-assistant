"""Opt-in isolated comparison of models on one fixed candidate-evidence input.

RUN_CANDIDATE_ASSESSMENT_EVALUATION=1 enables paid calls. Named configurations
come from EVALUATION_MODEL_CONFIGURATIONS, shared with the full-run suite; this
test uses evaluation_model_id and never runs parsing or retrieval. Results are
saved under test-evaluation-results/candidate-assessment/<STPY-run-id>/.
"""

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from typing import Any

import pytest
from langchain_core.messages import AIMessage, convert_to_messages
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse, propagate_attributes

from stone_shelter_assistant.assistant.candidate_evidence import CandidateEvidence
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler, provider_error_details
from stone_shelter_assistant.assistant.workflow import model_call_details, structured_model
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings
from tests.evaluation.support.candidate_assessment import CHECKS, check_assessment, score_checks
from tests.evaluation.support.model_configurations import ModelConfiguration, model_configurations
from tests.evaluation.support.run_identity import (
    EvaluationRunIdentity,
    comparison_id_from_environment,
    first_run_number_from_environment,
)
from tests.evaluation.support.run_records import (
    capture_telemetry,
    reserve_run_directory,
    write_json,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "fixtures/assistant/quiet-home-assessment.json"
pytestmark = pytest.mark.skipif(
    os.getenv("RUN_CANDIDATE_ASSESSMENT_EVALUATION") != "1",
    reason="Explicit paid candidate-assessment opt-in required",
)


@pytest.fixture(scope="module")
def assessment_comparison() -> str:
    return comparison_id_from_environment(datetime.now(UTC))


@pytest.mark.parametrize("configuration", model_configurations(), ids=lambda item: item.name)
@pytest.mark.asyncio
@pytest.mark.acceptance("AC-EVIDENCE-01")
async def test_frozen_assessment_across_models(
    configuration: ModelConfiguration, assessment_comparison: str
) -> None:
    snapshot = json.loads(SNAPSHOT.read_text())
    assert snapshot["schema"] == CandidateEvidence.model_json_schema()
    index = next(
        i for i, item in enumerate(model_configurations()) if item.name == configuration.name
    )
    identity = EvaluationRunIdentity.create(
        assessment_comparison, first_run_number_from_environment() + index
    )
    folder = reserve_run_directory(
        ROOT / "test-evaluation-results/candidate-assessment", identity.run_id
    )
    version = hashlib.sha256(SNAPSHOT.read_bytes()).hexdigest()
    code_hashes = {
        path.relative_to(ROOT).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [
            *list((ROOT / "src").rglob("*.py")),
            ROOT / "tests/evaluation/support/run_identity.py",
            Path(__file__),
            ROOT / "tests/evaluation/support/candidate_assessment.py",
            ROOT / "tests/evaluation/support/model_configurations.py",
            ROOT / "tests/evaluation/support/run_records.py",
        ]
    }
    record: dict[str, Any] = {
        **identity.as_metadata(),
        "session_id": identity.session_id,
        "status": "prepared",
        "mode": "candidate-assessment",
        "case_id": snapshot["eval_case_id"],
        "model_id": configuration.evaluation_model_id,
        "configuration": configuration.model_dump(),
        "max_retries": 0,
        "request_timeout": 180_000,
        "fixture_sha256": version,
        "code_hashes": code_hashes,
        "input": snapshot,
        "trace_id": None,
        **dict.fromkeys(CHECKS, False),
    }
    write_json(
        folder / "manifest.json",
        {
            key: record[key]
            for key in (
                "mode",
                "case_id",
                "comparison_id",
                "run_number",
                "run_id",
                "session_id",
                "model_id",
                "configuration",
                "max_retries",
                "request_timeout",
                "fixture_sha256",
                "code_hashes",
            )
        },
    )

    def persist() -> None:
        write_json(
            folder / "result.json",
            {key: value for key, value in record.items() if key != "observations"},
        )
        write_json(
            folder / "observations.json",
            {
                "trace_id": record["trace_id"],
                "observations": record.get("observations", []),
                "telemetry_errors": record.get("telemetry_errors", []),
            },
        )

    persist()
    client: Langfuse | None = None
    started = monotonic()
    try:
        tracing = LangfuseSettings()
        settings = OpenRouterSettings()
        client = Langfuse(
            public_key=tracing.public_key,
            secret_key=tracing.secret_key.get_secret_value(),
            base_url=tracing.base_url,
        )
        dataset_name = "STPY-quiet-home-candidate-assessment"
        client.create_dataset(
            name=dataset_name, description="Fixed candidate evidence and reviewed checks"
        )
        dataset_item = client.create_dataset_item(
            dataset_name=dataset_name,
            id=f"{dataset_name}-quiet-home-{version[:24]}",
            input=snapshot,
            expected_output={
                "confirmed_character_names": [card["name"] for card in snapshot["cards"]],
                "individual_compatibility": [],
            },
            metadata={"snapshot_sha256": version, "fixture_version": snapshot["fixture_version"]},
        )

        async def task(*, item: Any, **kwargs: Any) -> dict[str, Any]:
            assert client is not None
            with client.start_as_current_observation(name="evaluate_candidates") as stage:
                record.update(trace_id=stage.trace_id, status="running")
                persist()
                try:
                    model = ChatOpenRouter(
                        model_name=configuration.evaluation_model_id,
                        openrouter_api_key=settings.api_key,
                        max_tokens=configuration.max_tokens,
                        max_retries=0,
                        request_timeout=180_000,
                    )
                    use_json_schema = (
                        configuration.evaluation_model_id in settings.evaluation_json_schema_models
                    )
                    record["use_json_schema"] = use_json_schema
                    _, runnable = structured_model(
                        model,
                        CandidateEvidence,
                        use_json_schema=use_json_schema,
                        reasoning={"effort": configuration.reasoning_effort},
                    )
                    response = await runnable.ainvoke(
                        convert_to_messages(item.input["messages"]),
                        config={
                            "callbacks": [
                                WorkflowTraceHandler(
                                    public_key=tracing.public_key,
                                    trace_context={
                                        "trace_id": stage.trace_id,
                                        "parent_span_id": stage.id,
                                    },
                                )
                            ],
                        },
                    )
                    raw = response.get("raw") if isinstance(response, dict) else None
                    parsed = response.get("parsed") if isinstance(response, dict) else None
                    if isinstance(raw, AIMessage):
                        record["model_call"] = model_call_details(raw)
                        record["raw_response"] = raw.model_dump(mode="json")
                    if (
                        isinstance(raw, AIMessage)
                        and raw.response_metadata.get("finish_reason") == "length"
                    ):
                        raise ValueError("Candidate assessment reached the output token limit")
                    if not isinstance(parsed, CandidateEvidence):
                        raise ValueError("Model returned no current CandidateEvidence assessment")
                    record.update(check_assessment(parsed, item.input), status="completed")
                except Exception as error:
                    record.update(
                        status="assessment_failed",
                        error_type=type(error).__name__,
                        provider_error=provider_error_details(error),
                    )
                record["passed"] = record["status"] == "completed" and all(
                    record[name] for name in CHECKS
                )
                persist()
                try:
                    stage.update(output={key: record[key] for key in (*CHECKS, "status", "passed")})
                except Exception as error:
                    record.setdefault("telemetry_errors", []).append(type(error).__name__)
                    persist()
            return {key: record[key] for key in (*CHECKS, "passed", "status")}

        with propagate_attributes(
            user_id="STPY-local-test-user",
            session_id=identity.session_id,
            metadata=identity.as_metadata(),
        ):
            experiment = await asyncio.to_thread(
                client.run_experiment,
                name=dataset_name,
                run_name=identity.run_id,
                data=[dataset_item],
                task=task,
                evaluators=[score_checks],
                max_concurrency=1,
                metadata={"model_id": configuration.evaluation_model_id, "fixture_sha256": version},
            )
        record["experiment_url"] = experiment.experiment_url
    except Exception as error:
        if record["status"] not in {"completed", "assessment_failed"}:
            record.update(
                status="execution_failed",
                error_type=type(error).__name__,
                provider_error=provider_error_details(error),
            )
        else:
            record.setdefault("telemetry_errors", []).append(type(error).__name__)
    finally:
        record["elapsed_seconds"] = round(monotonic() - started, 3)
        persist()
        if client is not None and record["trace_id"] is not None:
            await capture_telemetry(client, record["trace_id"], record, persist)
    assert record["status"] == "completed", f"Assessment failed; inspect {folder / 'result.json'}"
    assert record["passed"], f"Evidence checks failed; inspect {folder / 'result.json'}"
