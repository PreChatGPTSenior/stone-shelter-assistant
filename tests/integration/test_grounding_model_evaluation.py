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
from tests.evaluation.grounding_cases import parsed_grounding_case

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.core.settings import (
    LangfuseSettings,
    OpenRouterSettings,
    TypesenseSettings,
)
from stone_shelter_assistant.search.infrastructure.client_factories import create_typesense_client
from stone_shelter_assistant.search.knowledge.grounding_catalog import GroundingCatalog

ROOT = Path(__file__).parents[2]
CASE_DIR = ROOT / "tests/fixtures/agent-eval/grounding-en"


def grounding_metrics(
    expected: list[str], actual: list[str | None]
) -> dict[str, float | int | None]:
    if not expected or len(expected) != len(actual):
        raise ValueError("Expected aligned, nonempty measurements")
    positives = sum(value == "supported" for value in actual)
    true_positive = sum(e == a == "supported" for e, a in zip(expected, actual, strict=True))
    return {
        "count": len(expected),
        "technical_failures": sum(value is None for value in actual),
        "classification_accuracy": sum(e == a for e, a in zip(expected, actual, strict=True))
        / len(expected),
        "acceptance_accuracy": sum(
            a is not None and (e == "supported") == (a == "supported")
            for e, a in zip(expected, actual, strict=True)
        )
        / len(expected),
        "false_acceptances": sum(
            a == "supported" and e != "supported" for e, a in zip(expected, actual, strict=True)
        ),
        "supported_precision": true_positive / positives if positives else None,
    }


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
    rows = []
    try:
        catalog = GroundingCatalog(search, language="en", version="en-v1")
        snapshot = await catalog.reload(ROOT / "fixtures/knowledge/grounding/grounding_en-v1.json")
        context: Any = SimpleNamespace(
            grounding_catalog=catalog,
            evaluation_model=model,
            evaluation_uses_json_schema=model_id
            in OpenRouterSettings().evaluation_json_schema_models,
            evaluation_reasoning={"effort": "medium"},
        )
        for case in cases:
            parsed = parsed_grounding_case(case)

            async def verify(state: Any) -> dict[str, object]:
                return await workflow.ground_question(state, runtime=Runtime(context=context))

            started = monotonic()
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
                root.update(
                    output={"finding": actual, "grounding_status": output.get("grounding_status")}
                )
                trace_id = root.trace_id
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
            rows.append(
                {
                    "case": case,
                    "actual": actual,
                    "result": output,
                    "seconds": monotonic() - started,
                    "trace_id": trace_id,
                    "observations": [o.model_dump(mode="json") for o in observations],
                }
            )
        expected = [case["expected"] for case in cases]
        result = {
            "model_id": model_id,
            "max_tokens": 8192,
            "reasoning_effort": "medium",
            "max_retries": 0,
            "catalog": snapshot.model_dump(mode="json"),
            "rows": rows,
            "holdout_hash": hashlib.sha256((CASE_DIR / "holdout.json").read_bytes()).hexdigest(),
            "metrics": grounding_metrics(expected, [row["actual"] for row in rows]),
            "historical_regex_acceptance_accuracy": sum(
                case["historical_regex_accepted"] == (case["expected"] == "supported")
                for case in cases
            )
            / len(cases),
            "note": "Historical binary outcomes are frozen data, not a retained legacy implementation. Expected labels are never sent to the model; training examples use different wording. No quality success assertion.",
        }
        folder = CASE_DIR / "runs"
        folder.mkdir(exist_ok=True)
        (folder / (datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ") + ".json")).write_text(
            json.dumps(result, default=encoded, ensure_ascii=False, indent=2) + "\n"
        )
    finally:
        await search.api_call.aclose()
    assert len(rows) == len(cases)
