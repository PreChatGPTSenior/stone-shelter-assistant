"""Opt-in calibration of a semantic judge on frozen reference answers, not app quality."""

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse, propagate_attributes

from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.assistant.workflow import structured_model
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings
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
from tests.synthetic_evaluation.support.answer_assertions import (
    AnswerAssessment,
    AssertionCase,
    archive_judge_result,
    assessment_messages,
    assessment_report,
    calibration_metrics,
    load_case_sources,
    validate_assessment,
)

ROOT = Path(__file__).parents[2]
FOLDER = ROOT / "fixtures/agent-eval/reference-answer-assertions"


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_ANSWER_ASSERTION_EVALUATION") != "1",
    reason="Explicit semantic-judge calibration opt-in required",
)
async def test_calibrate_reference_answer_assertion_judge() -> None:
    model_id = os.getenv("ANSWER_ASSERTIONS_JUDGE_MODEL")
    assert model_id, "Choose ANSWER_ASSERTIONS_JUDGE_MODEL explicitly before authorizing calls"
    settings = OpenRouterSettings()
    tracing = LangfuseSettings()
    model = ChatOpenRouter(
        model_name=model_id,
        openrouter_api_key=settings.api_key,
        max_tokens=4096,
        max_retries=0,
        request_timeout=180_000,
    )
    _, judge = structured_model(
        model,
        AnswerAssessment,
        use_json_schema=model_id in settings.evaluation_json_schema_models,
        reasoning={"effort": "medium"},
    )
    client = Langfuse(
        public_key=tracing.public_key,
        secret_key=tracing.secret_key.get_secret_value(),
        base_url=tracing.base_url,
    )
    cases = [
        AssertionCase.model_validate(c)
        for c in json.loads((FOLDER / "cases.json").read_text())["cases"]
    ]
    paths = {FOLDER / "cases.json", *(ROOT / s.file for c in cases for s in c.sources)}
    fixture_hashes = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(paths)
    }
    records: list[dict[str, Any]] = []
    measurements: list[tuple[dict[str, bool], AnswerAssessment | None]] = []
    identity = EvaluationRunIdentity.create(
        comparison_id_from_environment(datetime.now(UTC)), first_run_number_from_environment()
    )
    output = reserve_run_directory(
        ROOT / "test-evaluation-results/reference-answer-assertions", identity.run_id
    )
    archive_path = output / "result.json"
    code_hashes = {
        str(path.relative_to(ROOT)): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in [
            *list((ROOT / "src").rglob("*.py")),
            ROOT / "tests/evaluation/support/run_identity.py",
            Path(__file__),
            ROOT / "tests/synthetic_evaluation/support/answer_assertions.py",
            ROOT / "tests/evaluation/support/run_records.py",
        ]
    }
    status = "running"
    write_json(
        output / "manifest.json",
        {
            **identity.as_metadata(),
            "session_id": identity.session_id,
            "mode": "frozen-answer-judge-calibration",
            "judge_model": model_id,
            "judge_schema": AnswerAssessment.model_json_schema(),
            "fixture_hashes": fixture_hashes,
            "code_hashes": code_hashes,
            "reasoning_effort": "medium",
            "max_tokens": 4096,
            "max_retries": 0,
        },
    )

    def persist_archive() -> None:
        result = {
            "mode": "frozen-answer-judge-calibration",
            **identity.as_metadata(),
            "status": status,
            "session_id": identity.session_id,
            "code_hashes": code_hashes,
            "judge_model": model_id,
            "reasoning_effort": "medium",
            "max_tokens": 4096,
            "max_retries": 0,
            "fixture_hashes": fixture_hashes,
            "metrics": calibration_metrics(measurements) if measurements else None,
            "records": [
                {k: v for k, v in record.items() if k != "observations"} for record in records
            ],
            "note": "No application search/answer generation. Calibration does not establish universal semantic correctness.",
        }
        write_json(archive_path, result)
        write_json(
            output / "observations.json",
            {
                "session_id": identity.session_id,
                "records": [
                    {
                        "trace_id": record.get("trace_id"),
                        "case_id": record["case_id"],
                        "sample_id": record["sample_id"],
                        "observations": record.get("observations", []),
                        "telemetry_errors": record.get("telemetry_errors", []),
                    }
                    for record in records
                ],
            },
        )

    persist_archive()

    for case in cases:
        sources = load_case_sources(case, ROOT)
        for sample in case.samples:
            parsed: AnswerAssessment | None = None
            record: dict[str, Any] = {
                "case_id": case.id,
                "sample_id": sample.id,
                "question": case.question,
                "sample": sample.model_dump(mode="json"),
                "sources": [s.model_dump(mode="json") for s in sources],
            }
            record["judge_messages"] = [
                m.model_dump(mode="json") for m in assessment_messages(case, sample, sources)
            ]
            with (
                propagate_attributes(
                    user_id="STPY-local-test-user",
                    session_id=identity.session_id,
                    metadata=identity.as_metadata(),
                ),
                client.start_as_current_observation(name="answer_assertion_calibration") as root,
            ):
                root.update(
                    input={"case_id": case.id, "sample_id": sample.id, "judge_model": model_id}
                )
                try:
                    response = await judge.ainvoke(
                        assessment_messages(case, sample, sources),
                        config={
                            "run_name": "answer_assertion_judge",
                            "callbacks": [
                                WorkflowTraceHandler(
                                    public_key=tracing.public_key,
                                    trace_context={
                                        "trace_id": root.trace_id,
                                        "parent_span_id": root.id,
                                    },
                                )
                            ],
                        },
                    )
                    proposed = response.get("parsed") if isinstance(response, dict) else None
                    raw = response.get("raw") if isinstance(response, dict) else None
                    if (
                        not isinstance(proposed, AnswerAssessment)
                        or raw is None
                        or raw.response_metadata.get("finish_reason") == "length"
                    ):
                        raise ValueError("Judge did not return a complete assessment")
                    record["assessment"] = proposed.model_dump(mode="json")
                    record["report"] = assessment_report(case, sample, sources, proposed)
                    validate_assessment(case, sample, sources, proposed)
                    parsed = proposed
                except Exception as error:
                    parsed = None
                    record["technical_error_type"] = type(error).__name__
                record["trace_id"] = root.trace_id
                archive_judge_result(
                    record, sample.expected, parsed, records, measurements, persist_archive
                )
                if parsed is not None:
                    for finding in parsed.findings:
                        try:
                            client.create_score(
                                trace_id=root.trace_id,
                                name="assertion." + finding.assertion_id,
                                value=float(finding.verdict == "pass"),
                                comment=finding.verdict + ": " + finding.reason,
                            )
                        except Exception as error:
                            record.setdefault("telemetry_errors", []).append(type(error).__name__)
                try:
                    root.update(
                        output={
                            k: record[k] for k in ("report", "technical_error_type") if k in record
                        }
                    )
                except Exception as error:
                    record.setdefault("telemetry_errors", []).append(type(error).__name__)
                persist_archive()
            await capture_telemetry(client, record["trace_id"], record, persist_archive)
    metrics = calibration_metrics(measurements)
    status = (
        "completed"
        if all(
            metrics[key] == 0
            for key in ("false_passes", "false_failures", "abstentions", "technical_errors")
        )
        else "calibration_failed"
    )
    persist_archive()
    assert all(
        metrics[key] == 0
        for key in ("false_passes", "false_failures", "abstentions", "technical_errors")
    ), metrics
