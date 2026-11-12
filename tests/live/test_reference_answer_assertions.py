"""Opt-in calibration of a semantic judge on frozen reference answers, not app quality."""

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse
from tests.evaluation.answer_assertions import (
    AnswerAssessment,
    AssertionCase,
    assessment_messages,
    assessment_report,
    calibration_metrics,
    load_case_sources,
    validate_assessment,
)

from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.assistant.workflow import structured_model
from stone_shelter_assistant.core.settings import LangfuseSettings, OpenRouterSettings

ROOT = Path(__file__).parents[2]
FOLDER = ROOT / "tests/fixtures/agent-eval/reference-answer-assertions"


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
    records = []
    measurements = []
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
            with client.start_as_current_observation(name="answer_assertion_calibration") as root:
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
                    for finding in parsed.findings:
                        client.create_score(
                            trace_id=root.trace_id,
                            name="assertion." + finding.assertion_id,
                            value=float(finding.verdict == "pass"),
                            comment=finding.verdict + ": " + finding.reason,
                        )
                except Exception as error:
                    parsed = None
                    record["technical_error_type"] = type(error).__name__
                record["trace_id"] = root.trace_id
                root.update(
                    output={k: record[k] for k in ("report", "technical_error_type") if k in record}
                )
            measurements.append((sample.expected, parsed))
            await asyncio.to_thread(client.flush)
            observations = []
            for _ in range(8):
                observations = (
                    await asyncio.to_thread(
                        client.api.observations.get_many,
                        trace_id=record["trace_id"],
                        fields="basic,io,model,usage",
                        limit=100,
                    )
                ).data
                if any(o.type == "GENERATION" and o.output for o in observations):
                    break
                await asyncio.sleep(2)
            record["observations"] = [o.model_dump(mode="json") for o in observations]
            records.append(record)
    metrics = calibration_metrics(measurements)
    paths = {FOLDER / "cases.json", *(ROOT / s.file for c in cases for s in c.sources)}
    result = {
        "mode": "frozen-answer-judge-calibration",
        "judge_model": model_id,
        "reasoning_effort": "medium",
        "max_tokens": 4096,
        "max_retries": 0,
        "fixture_hashes": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(paths)
        },
        "metrics": metrics,
        "records": records,
        "note": "No application search/answer generation. Calibration does not establish universal semantic correctness.",
    }
    output = FOLDER / "runs"
    output.mkdir(exist_ok=True)
    (output / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json")).write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    )
    assert all(
        metrics[key] == 0
        for key in ("false_passes", "false_failures", "abstentions", "technical_errors")
    ), metrics
