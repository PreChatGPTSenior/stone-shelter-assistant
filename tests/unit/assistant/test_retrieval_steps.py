"""Check retrieval tool selection, call allowances and fused-hit collection directly."""

import json
from types import SimpleNamespace
from typing import Any

import pytest
from langchain_core.messages import ToolMessage
from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.selection import (
    RetrievalRequest,
)
from stone_shelter_assistant.assistant.tool_planning import ReferenceRequest


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "named,used,expected",
    [(False, 0, "search_stones_hybrid"), (True, 0, "search_stones_lexical"), (False, 3, None)],
)
@pytest.mark.acceptance("AC-FLOW-02")
async def test_retrieval_routes_and_two_call_allowance(
    named: bool, used: int, expected: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})

    @tool
    async def search_stones_hybrid(
        lexical_query: str, semantic_query: str, filters: dict[str, Any]
    ) -> dict[str, Any]:
        """Fixture hybrid search."""
        return {"candidates": [], "dropped": []}

    search_stones_hybrid.metadata = {"retrieval_calls": 2}

    @tool
    async def search_stones_lexical(query: str) -> list[dict[str, Any]]:
        """Fixture name search."""
        return []

    context: Any = SimpleNamespace(
        tool_executor=ToolNode([search_stones_hybrid, search_stones_lexical])
    )
    state: workflow.SearchState = {
        "question": "fixture",
        "messages": [],
        "tools_used": used,
        "reference_request": ReferenceRequest(
            stone_name="Sir Pebble" if named else None,
            recommendation_name="Sir Pebble" if named else None,
            care_types=[],
            pairs=[],
            pair_lists=[],
        ),
        "retrieval": RetrievalRequest.model_validate(
            {"lexical_query": "quiet", "semantic_query": "quiet home", "filters": {}}
        ),
    }
    result = await workflow.search_candidates(state, runtime=Runtime(context=context))
    if expected is None:
        assert result["stop_reason"] == "retrieval_call_limit"
        return
    messages = result["messages"]
    assert isinstance(messages, list)
    reply: Any = messages[0]
    assert reply.tool_calls[0]["name"] == expected
    state["messages"] = [reply]
    update = await workflow.tools(state, runtime=Runtime(context=context))
    assert update["tools_used"] == used + (1 if named else 2)


@pytest.mark.acceptance("AC-FLOW-03")
@pytest.mark.acceptance("AC-RETRIEVAL-01")
def test_collector_excludes_hits_dropped_by_fusion() -> None:
    state: workflow.SearchState = {
        "question": "fixture",
        "tools_used": 2,
        "messages": [
            ToolMessage(
                name="search_stones_hybrid",
                tool_call_id="search",
                content=json.dumps(
                    {
                        "candidates": [{"card": {"id": "kept"}}],
                        "dropped": [{"card": {"id": "dropped"}}],
                    }
                ),
            )
        ],
    }
    assert list(workflow.retrieved_candidates(state)) == ["kept"]
