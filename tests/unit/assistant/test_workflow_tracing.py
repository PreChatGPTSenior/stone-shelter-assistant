import json
from typing import Any, TypedDict
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import tool
from langchain_openrouter import ChatOpenRouter
from langfuse import Langfuse
from langgraph.config import get_config
from langgraph.graph import END, START, StateGraph
from opentelemetry.sdk.trace import ReadableSpan, TracerProvider
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter
from pydantic import BaseModel, SecretStr

from stone_shelter_assistant.assistant.tracing import WorkflowTraceHandler, trace_result


class TraceState(TypedDict, total=False):
    messages: list[HumanMessage]
    criteria_status: str
    result: dict[str, Any]


class ParsedQuestion(BaseModel):
    subject: str


def span_payload(span: ReadableSpan, field: str) -> Any:
    assert span.attributes is not None
    value = span.attributes[f"langfuse.observation.{field}"]
    assert isinstance(value, str)
    return json.loads(value)


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ['{"subject":"obsidian"}', ""])
async def test_tracing_keeps_model_and_decisions_without_framework_payloads(
    monkeypatch: pytest.MonkeyPatch, response: str
) -> None:
    model_inputs = []

    async def generate(
        self: ChatOpenRouter, messages: list[BaseMessage], **kwargs: Any
    ) -> ChatResult:
        model_inputs.append([message.content for message in messages])
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=response))])

    monkeypatch.setattr(ChatOpenRouter, "_agenerate", generate)
    exporter = InMemorySpanExporter()
    public_key = f"test-{uuid4()}"
    client = Langfuse(
        public_key=public_key,
        secret_key="test-secret",
        tracer_provider=TracerProvider(),
        span_exporter=exporter,
    )
    model = ChatOpenRouter(model_name="test-model", openrouter_api_key=SecretStr("test-key"))
    structured = model.with_structured_output(
        ParsedQuestion, method="json_schema", include_raw=True
    )

    async def parse_question(state: TraceState) -> dict[str, str]:
        result = await structured.ainvoke(state["messages"], config=get_config())
        assert isinstance(result, dict)
        return {"criteria_status": "parsed" if result["parsed"] else "invalid_response"}

    def after_parsing(state: TraceState) -> str:
        return "answer"

    @tool
    def read_source() -> dict[str, str]:
        """Read one source document."""
        return {"source_key": "source-1", "text": "Full source document"}

    async def answer(state: TraceState) -> dict[str, Any]:
        for _ in range(2):
            document = await read_source.ainvoke({}, config=get_config())
            assert document["text"] == "Full source document"
        await model.ainvoke(
            [HumanMessage(content=json.dumps({"encyclopedia": document["text"]}))],
            config=get_config(),
        )
        return {
            "result": {
                "answer": "Final answer",
                "recommended_stone_ids": ["stone-1"],
                "sources": {"source-1": {"text": "Full source document"}},
            }
        }

    builder = StateGraph(TraceState)
    builder.add_node("parse_question", parse_question)
    builder.add_node("answer", answer)
    builder.add_edge(START, "parse_question")
    builder.add_conditional_edges("parse_question", after_parsing, {"answer": "answer"})
    builder.add_edge("answer", END)
    with client.start_as_current_observation(name="questions") as root:
        callback = WorkflowTraceHandler(
            public_key=public_key,
            trace_context={"trace_id": root.trace_id, "parent_span_id": root.id},
        )
        state = await builder.compile().ainvoke(
            {"messages": [HumanMessage(content="Question")]},
            config={"callbacks": [callback], "run_name": "search-workflow"},
        )
        root.update(output=trace_result(state["result"], include_answer=True))
    client.flush()
    spans = exporter.get_finished_spans()
    by_name = {span.name: span for span in spans}
    assert all(span.context.trace_id == spans[0].context.trace_id for span in spans)
    assert not any(span.name.startswith(("Runnable", "Pydantic", "after_")) for span in spans)
    stage = by_name["parse_question"]
    generation = next(
        span
        for span in spans
        if span.name == "ChatOpenRouter"
        and span.parent is not None
        and span.parent.span_id == stage.context.span_id
    )
    assert generation.parent is not None
    assert generation.parent.span_id == stage.context.span_id
    assert "Question" in json.dumps(span_payload(generation, "input"))
    assert "messages" not in span_payload(stage, "input")
    stage_output = span_payload(stage, "output")
    assert stage_output["next_stage"] == "answer"
    assert bool(stage_output.get("validation_errors")) == (not response)
    tool_spans = [span for span in spans if span.name == "read_source"]
    assert len(tool_spans) == 2
    assert all(
        span.parent is not None and span.parent.span_id == by_name["answer"].context.span_id
        for span in tool_spans
    )
    first_source = span_payload(tool_spans[0], "output")
    repeated_source = span_payload(tool_spans[1], "output")
    assert first_source["text"] == "Full source document"
    assert repeated_source == {
        "source_ref": "source-1",
        "observation_id": f"{tool_spans[0].context.span_id:016x}",
    }
    traced_input = json.dumps(span_payload(by_name["ChatOpenRouter"], "input"))
    assert "Full source document" not in traced_input
    assert "source-1" in traced_input
    assert "Full source document" in str(model_inputs[-1])
    graph_output = span_payload(by_name["search-workflow"], "output")
    assert graph_output == {"recommended_stone_ids": ["stone-1"], "source_refs": ["source-1"]}
    assert state["result"]["sources"]["source-1"]["text"] == "Full source document"
    client.shutdown()
