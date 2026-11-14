"""Explicitly authorized semantic-grounding measurement, with isolated storage."""

import asyncio
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from time import monotonic
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.runnables import RunnableLambda
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse
from langgraph.runtime import Runtime
from pydantic import BaseModel

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler, provider_error_details
from stone_shelter_assistant.core.settings import (
    LangfuseSettings,
    OpenRouterSettings,
    TypesenseSettings,
)
from stone_shelter_assistant.search.infrastructure.client_factories import create_typesense_client
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingConceptStoreService,
)
from tests.evaluation.support.grounding_cases import grounding_metrics, parsed_grounding_case
from tests.integration.conftest import typesense_container as typesense_container
from tests.integration.conftest import typesense_settings as typesense_settings

ROOT = Path(__file__).parents[2]
CASE_DIR = ROOT / "fixtures/agent-eval/grounding-en"


def encoded(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    raise TypeError(type(value).__name__)


@pytest.mark.asyncio
@pytest.mark.skipif(
    os.getenv("RUN_GROUNDING_EVALUATION") != "1",
    reason="Explicit paid grounding evaluation opt-in required",
)
async def test_measure_grounding_on_held_out_questions(
    typesense_settings: TypesenseSettings,
) -> None:
    settings = LangfuseSettings()
    client = Langfuse(
        public_key=settings.public_key,
        secret_key=settings.secret_key.get_secret_value(),
        base_url=settings.base_url,
    )
    model_id = os.getenv("GROUNDING_EVALUATION_MODEL", "openai/gpt-6-luna")
    model = ChatOpenRouter(
        model_name=model_id,
        openrouter_api_key=OpenRouterSettings().api_key,
        max_tokens=8192,
        max_retries=0,
        request_timeout=180_000,
    )
    search = create_typesense_client(typesense_settings)
    cases = json.loads((CASE_DIR / "holdout.json").read_text())
    acceptance_mode = os.getenv("RUN_GROUNDING_ACCEPTANCE") == "1"
    rows: list[dict[str, Any]] = []
    try:
        catalog = GroundingConceptStoreService(search, language="en", version="en-v1")
        snapshot = await catalog.reload(ROOT / "fixtures/knowledge/grounding/grounding_en-v1.json")
        context: Any = SimpleNamespace(
            grounding_catalog=catalog,
            evaluation_model=model,
            evaluation_uses_json_schema=model_id
            in OpenRouterSettings().evaluation_json_schema_models,
            evaluation_reasoning={"effort": "medium"},
        )
        folder = ROOT / "test-evaluation-results/grounding-en"
        folder.mkdir(parents=True, exist_ok=True)
        archive = folder / (datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ") + ".json")
        holdout_hash = hashlib.sha256((CASE_DIR / "holdout.json").read_bytes()).hexdigest()

        def checkpoint() -> None:
            completed = rows
            partial = {
                "mode": "acceptance" if acceptance_mode else "diagnostic",
                "model_id": model_id,
                "max_tokens": 8192,
                "reasoning_effort": "medium",
                "max_retries": 0,
                "catalog": snapshot.model_dump(mode="json"),
                "rows": completed,
                "holdout_hash": holdout_hash,
                "metrics": grounding_metrics(
                    [row["case"]["expected"] for row in completed],
                    [row["actual"] for row in completed],
                )
                if completed
                else None,
                "note": (
                    "Expected labels are never sent to the model. Acceptance mode requires every reviewed "
                    "holdout outcome; diagnostic mode records mismatches without a semantic pass claim."
                ),
            }
            archive.write_text(
                json.dumps(partial, default=encoded, ensure_ascii=False, indent=2) + "\n"
            )

        for case in cases:
            started = monotonic()
            completed_row: dict[str, Any] | None = None
            root: Any = None
            try:
                parsed = parsed_grounding_case(case)

                async def verify(state: Any) -> dict[str, object]:
                    return await workflow.ground_question(state, runtime=Runtime(context=context))

                with client.start_as_current_observation(name="grounding_evaluation") as root:
                    root.update(
                        input={
                            "case_id": case["id"],
                            "original_question": case["question"],
                            "catalog_hash": snapshot.content_hash,
                            "model_id": model_id,
                        }
                    )
                    output = await RunnableLambda(verify, name="ground_question").ainvoke(
                        {
                            "question": case["question"],
                            "question_fragments": {1: case["question"]},
                            "parsed_question": parsed,
                            "grounding_catalog_snapshot": snapshot.model_dump(mode="json"),
                        },
                        config={
                            "callbacks": [
                                WorkflowTraceHandler(
                                    public_key=settings.public_key,
                                    trace_context={
                                        "trace_id": root.trace_id,
                                        "parent_span_id": root.id,
                                    },
                                )
                            ]
                        },
                    )
                    decisions = output.get("grounding_decisions", [])
                    actual = (
                        decisions[0]["finding"]
                        if output.get("grounding_status") == "verified" and decisions
                        else None
                    )
                    trace_id = root.trace_id
                    completed_row = {
                        "case": case,
                        "actual": actual,
                        "result": output,
                        "seconds": monotonic() - started,
                        "trace_id": trace_id,
                        "observations": [],
                    }
                    rows.append(completed_row)
                    checkpoint()
                    root.update(
                        output={
                            "finding": actual,
                            "grounding_status": output.get("grounding_status"),
                        }
                    )
                await asyncio.to_thread(client.flush)
                observations = []
                for _ in range(8):
                    observations = (
                        await asyncio.to_thread(
                            client.api.observations.get_many,
                            trace_id=trace_id,
                            fields="basic,io,model,usage",
                            limit=100,
                        )
                    ).data
                    if any(o.type == "GENERATION" and o.output for o in observations):
                        break
                    await asyncio.sleep(2)
                completed_row["observations"] = [o.model_dump(mode="json") for o in observations]
            except Exception as error:
                failure: dict[str, Any] = {"type": type(error).__name__}
                details = provider_error_details(error)
                if details is not None:
                    failure["provider"] = details
                if completed_row is not None:
                    completed_row["export_error"] = failure
                else:
                    failed_row: dict[str, Any] = {
                        "case": case,
                        "actual": None,
                        "technical_error": failure,
                        "seconds": monotonic() - started,
                    }
                    if root is not None:
                        failed_row["trace_id"] = root.trace_id
                    rows.append(failed_row)
            checkpoint()
        expected = [case["expected"] for case in cases]
        metrics = grounding_metrics(expected, [row["actual"] for row in rows])
        result = {
            "model_id": model_id,
            "max_tokens": 8192,
            "reasoning_effort": "medium",
            "max_retries": 0,
            "catalog": snapshot.model_dump(mode="json"),
            "rows": rows,
            "holdout_hash": holdout_hash,
            "metrics": metrics,
            "mode": "acceptance" if acceptance_mode else "diagnostic",
            "expected_case_ids": [case["id"] for case in cases],
            "observed_case_ids": [row["case"]["id"] for row in rows],
            "outcome_mismatches": [
                {
                    "case_id": row["case"]["id"],
                    "expected": row["case"]["expected"],
                    "actual": row["actual"],
                }
                for row in rows
                if row["actual"] != row["case"]["expected"]
            ],
            "technical_failures": [
                {"case_id": row["case"]["id"], **row["technical_error"]}
                for row in rows
                if row.get("technical_error")
            ],
            "unmeasured_case_ids": [
                row["case"]["id"] for row in rows if row["actual"] is None
            ],
            "note": (
                "Expected labels are never sent to the model. Acceptance mode requires every reviewed holdout outcome; "
                "diagnostic mode records outcome mismatches without a semantic pass claim. Telemetry export errors "
                "are archived separately from model/grounding failures."
            ),
        }
        archive.write_text(json.dumps(result, default=encoded, ensure_ascii=False, indent=2) + "\n")
    finally:
        await search.api_call.aclose()
    expected_ids = [case["id"] for case in cases]
    observed_ids = [row["case"]["id"] for row in rows]
    assert observed_ids == expected_ids, (
        f"Grounding cases are missing, duplicated, or reordered: {observed_ids}; archive: {archive}"
    )
    technical_failures = [row["case"]["id"] for row in rows if row.get("technical_error")]
    assert not technical_failures, (
        f"Grounding execution failed for {technical_failures}; archive: {archive}"
    )
    unmeasured = [row["case"]["id"] for row in rows if row["actual"] is None]
    assert not unmeasured, f"Grounding produced no usable finding for {unmeasured}; archive: {archive}"
    if acceptance_mode:
        mismatches = [
            row["case"]["id"]
            for row in rows
            if row["actual"] != row["case"]["expected"]
        ]
        assert not mismatches, (
            f"Reviewed grounding outcomes did not match for {mismatches}; archive: {archive}"
        )
