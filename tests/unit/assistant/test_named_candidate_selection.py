"""Check the selection function preserves resolved identities and rejects ambiguous names."""

import json
from types import SimpleNamespace
from typing import Any, cast
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.runnables import RunnableLambda
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.reference_lookup import ReferenceResult
from stone_shelter_assistant.assistant.selection import (
    ParseQuestion,
    SelectCandidates,
)
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-IDENTITY-01")
@pytest.mark.acceptance("AC-FLOW-03")
async def test_named_recommendation_rejects_a_different_retrieved_stone_id() -> None:
    target_id = uuid4()
    other_id = uuid4()
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    request = parsed.resolve_references({1: "Recommend Svetlana."})

    class UnexpectedModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            raise AssertionError("Selection must stop before accepting a different stone ID.")

    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": request,
        "reference_result": ReferenceResult(
            recommendation_stone=NamedStoneStatus(
                stone_id=target_id,
                name="Svetlana",
                stone_type=StoneType.MARBLE,
                adoption_status=AdoptionStatus.AVAILABLE,
            )
        ),
        "messages": [
            ToolMessage(
                name="search_stones_lexical",
                tool_call_id="search",
                content=json.dumps([{"id": str(other_id), "title": "Other stone"}]),
            )
        ],
    }
    context = SimpleNamespace(
        models=SimpleNamespace(
            selection_model=UnexpectedModel(),
            selection_uses_json_schema=True,
        ),
    )
    result = await workflow.select_candidates(state, runtime=Runtime(context=cast(Any, context)))
    assert result["selected_stone_ids"] == []
    assert result["selection_status"] == "named_candidate_not_retrieved"
    assert "no substitute was selected" in str(result["selection_note"])


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-IDENTITY-01")
@pytest.mark.acceptance("AC-FLOW-03")
async def test_named_recommendation_filters_model_selection_to_the_resolved_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(workflow, "get_config", lambda: {})
    target_id = uuid4()
    other_id = uuid4()
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 2,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    request = parsed.resolve_references({1: "Recommend Svetlana."})
    seen_cards: list[str] = []

    class FixtureModel:
        def with_structured_output(self, schema: Any, **kwargs: Any) -> Any:
            def select(messages: Any) -> dict[str, Any]:
                seen_cards.extend(
                    item["id"] for item in json.loads(messages[-1].content)["retrieved_cards"]
                )
                return {
                    "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                    "parsed": SelectCandidates(stone_ids=[str(target_id), str(other_id)]),
                }

            return RunnableLambda(select)

    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": request,
        "reference_result": ReferenceResult(
            recommendation_stone=NamedStoneStatus(
                stone_id=target_id,
                name="Svetlana",
                stone_type=StoneType.MARBLE,
                adoption_status=AdoptionStatus.AVAILABLE,
            )
        ),
        "messages": [
            ToolMessage(
                name="search_stones_lexical",
                tool_call_id="search",
                content=json.dumps(
                    [
                        {"id": str(target_id), "title": "Svetlana"},
                        {"id": str(other_id), "title": "Other stone"},
                    ]
                ),
            )
        ],
    }
    result = await workflow.select_candidates(
        state,
        runtime=Runtime(
            context=cast(
                Any,
                SimpleNamespace(
                    models=SimpleNamespace(
                        selection_model=FixtureModel(),
                        selection_uses_json_schema=True,
                    ),
                ),
            )
        ),
    )
    assert seen_cards == [str(target_id)]
    assert result["selected_stone_ids"] == [str(target_id)]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("issue", "message"),
    [("not_found", "No stone was found"), ("ambiguous", "matches multiple stones")],
)
@pytest.mark.acceptance("AC-IDENTITY-01")
@pytest.mark.acceptance("AC-FLOW-03")
async def test_named_recommendation_does_not_select_when_name_is_not_unique(
    issue: str, message: str
) -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
        }
    )
    criteria, _ = parsed.resolve({1: "Recommend Svetlana."})
    state: workflow.SearchState = {
        "question": "Recommend Svetlana.",
        "tools_used": 1,
        "criteria": criteria,
        "reference_request": parsed.resolve_references({1: "Recommend Svetlana."}),
        "reference_result": ReferenceResult(recommendation_issue=issue),
        "messages": [],
    }
    result = await workflow.select_candidates(
        state,
        runtime=Runtime(
            context=cast(
                Any,
                SimpleNamespace(
                    models=SimpleNamespace(
                        selection_model=SimpleNamespace(),
                        selection_uses_json_schema=True,
                    ),
                ),
            )
        ),
    )
    assert result["selected_stone_ids"] == []
    assert message in str(result["selection_note"])
