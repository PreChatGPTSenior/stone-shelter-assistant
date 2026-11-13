import json
from typing import Any, TypedDict
from uuid import uuid4

import httpx
import pytest
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from openrouter import OpenRouter
from openrouter.errors import BadRequestResponseError
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import SecretStr

from stone_shelter_assistant.assistant.candidate_evidence import CandidateEvidence
from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler
from stone_shelter_assistant.assistant.workflow import structured_model


class ErrorState(TypedDict):
    question: str


def _attribute_json(span: ReadableSpan, key: str) -> Any:
    assert span.attributes is not None
    value = span.attributes[key]
    assert isinstance(value, str)
    return json.loads(value)


@pytest.mark.asyncio
async def test_provider_error_metadata_is_attached_to_generation_and_stage() -> None:
    async def handle(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={
                "error": {
                    "code": 400,
                    "message": "Provider returned error",
                    "metadata": {
                        "provider_name": "OfflineProvider",
                        "raw": '{"error":{"message":"Invalid schema"},"headers":{"Authorization":"Bearer secret-value"}}',
                    },
                }
            },
        )

    http_client = httpx.AsyncClient(transport=httpx.MockTransport(handle))
    sdk_client = OpenRouter(api_key="offline-test-key", async_client=http_client, retry_config=None)
    model = ChatOpenRouter(
        model_name="test/model",
        openrouter_api_key=SecretStr("offline-test-key"),
        client=sdk_client,
    )
    _, structured = structured_model(model, CandidateEvidence, use_json_schema=True)

    async def stage(state: ErrorState) -> dict[str, str]:
        await structured.ainvoke(state["question"], config=get_config())
        return {"question": state["question"]}

    builder = StateGraph(ErrorState)
    builder.add_node("ground_question", stage)
    builder.add_edge(START, "ground_question")
    builder.add_edge("ground_question", END)

    exporter = InMemorySpanExporter()
    public_key = f"test-{uuid4()}"
    client = Langfuse(
        public_key=public_key,
        secret_key="test-secret",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
    )
    try:
        with client.start_as_current_observation(name="questions") as root:
            callback = WorkflowTraceHandler(
                public_key=public_key,
                trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
            )
            with pytest.raises(BadRequestResponseError):
                await builder.compile().ainvoke(
                    {"question": "question"},
                    config={"callbacks": [callback], "run_name": "search-workflow"},
                )
        client.flush()
        spans = exporter.get_finished_spans()
        generation = next(span for span in spans if span.name == "ChatOpenRouter")
        stage_span = next(span for span in spans if span.name == "ground_question")
        generation_errors = _attribute_json(
            generation, "langfuse.observation.metadata.validation_errors"
        )
        stage_errors = _attribute_json(
            stage_span, "langfuse.observation.metadata.validation_errors"
        )
        assert generation_errors[0]["provider_error"] == {
            "status_code": 400,
            "code": "400",
            "message": "Provider returned error",
            "provider_name": "OfflineProvider",
            "raw": {"error": {"message": "Invalid schema"}},
        }
        assert "Bearer secret-value" not in (generation.status.description or "")
        assert stage_errors[0]["provider_error"]["provider_name"] == "OfflineProvider"
        assert "Bearer secret-value" not in (stage_span.status.description or "")
    finally:
        client.shutdown()
        await http_client.aclose()
