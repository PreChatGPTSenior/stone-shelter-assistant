"""Verify selection receives parsed intent without calling a model."""

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_evaluation import SearchCriteria
from stone_shelter_assistant.assistant.selection import SelectCandidates
from stone_shelter_assistant.assistant.tool_planning import ReferenceRequest


@pytest.mark.asyncio
@pytest.mark.parametrize("has_criteria", [True, False])
async def test_selection_uses_parsed_requirements_preferences_and_household(
    monkeypatch: pytest.MonkeyPatch, has_criteria: bool
) -> None:
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "fragment_id": 1,
                    "question_quote": "A granite lives here.",
                    "existing_stone_type": "GRANITE",
                }
            ],
            "requirements": {
                "character": [{"fragment_id": 2, "question_quote": "Must tolerate children."}],
                "compatibility": [],
            },
            "preferences": {
                "character": [{"fragment_id": 3, "question_quote": "Quiet would be nice."}],
                "compatibility": [],
            },
        }
    )
    request = ReferenceRequest(stone_name=None, care_types=[], pairs=[], pair_lists=[])
    state: workflow.SearchState = {
        "question": "A granite lives here. Must tolerate children. Quiet would be nice.",
        "tools_used": 1,
        "messages": [
            ToolMessage(
                content=json.dumps([{"id": "gneiss", "title": "Brave Gneiss"}]),
                name="search_stones_lexical",
                tool_call_id="search",
            )
        ],
        "reference_request": request,
    }
    if has_criteria:
        state["criteria"] = criteria
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                "parsed": SelectCandidates(stone_ids=["gneiss", "invented"]),
            }
        )
    )
    build_model = Mock(return_value=("json_schema", model))
    monkeypatch.setattr(workflow, "structured_model", build_model)
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    runtime = Runtime(
        context=cast(
            workflow.RunContext,
            SimpleNamespace(
                selection_model=None,
                selection_uses_json_schema=True,
            ),
        )
    )
    result = await workflow.select_candidates(state, runtime=runtime)
    if not has_criteria:
        assert result["selection_status"] == "missing_criteria"
        assert result["selected_stone_ids"] == []
        build_model.assert_not_called()
        return
    messages = model.ainvoke.call_args.args[0]
    payload = json.loads(messages[1].content)
    assert payload["criteria"] == criteria.model_dump(mode="json")
    assert payload["reference_request"] == request.model_dump(mode="json")
    assert payload["question"] == state["question"]
    assert result["selected_stone_ids"] == ["gneiss"]
