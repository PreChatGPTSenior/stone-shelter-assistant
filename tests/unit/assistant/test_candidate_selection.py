"""Verify selection receives parsed intent without calling a model."""

import json
from types import SimpleNamespace
from typing import cast
from unittest.mock import AsyncMock, Mock

import pytest
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.selection import SelectCandidates
from stone_shelter_assistant.assistant.tool_planning import ReferenceRequest


@pytest.mark.asyncio
@pytest.mark.parametrize("has_criteria", [True, False])
@pytest.mark.acceptance("AC-QUESTION-01")
@pytest.mark.acceptance("AC-FLOW-03")
async def test_selection_uses_parsed_requirements_preferences_and_household(
    monkeypatch: pytest.MonkeyPatch, has_criteria: bool
) -> None:
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [
                {
                    "criterion_id": "household_fact.1",
                    "fragment_id": 1,
                    "question_quote": "A granite lives here.",
                    "existing_stone_type": "GRANITE",
                }
            ],
            "requirements": {
                "character": [
                    {
                        "criterion_id": "requirement.character.1",
                        "fragment_id": 2,
                        "question_quote": "Must tolerate children.",
                    }
                ],
                "compatibility": [],
            },
            "preferences": {
                "character": [
                    {
                        "criterion_id": "preference.character.1",
                        "fragment_id": 3,
                        "question_quote": "Quiet would be nice.",
                    }
                ],
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
                models=SimpleNamespace(
                    selection_model=None,
                    selection_uses_json_schema=True,
                ),
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


def _selection_state(candidate_ids: list[str]) -> workflow.SearchState:
    return {
        "question": "Find a suitable stone.",
        "tools_used": 1,
        "messages": [
            ToolMessage(
                content=json.dumps(
                    [{"id": stone_id, "title": stone_id.title()} for stone_id in candidate_ids]
                ),
                name="search_stones_lexical",
                tool_call_id="search",
            )
        ],
        "criteria": SearchCriteria.model_validate(
            {
                "recommendation_limit": 3,
                "household_facts": [],
                "requirements": {"character": [], "compatibility": []},
                "preferences": {"character": [], "compatibility": []},
            }
        ),
        "reference_request": ReferenceRequest(
            stone_name=None, care_types=[], pairs=[], pair_lists=[]
        ),
    }


def _selection_runtime() -> Runtime[workflow.RunContext]:
    return Runtime(
        context=cast(
            workflow.RunContext,
            SimpleNamespace(
                models=SimpleNamespace(
                    selection_model=None,
                    selection_uses_json_schema=True,
                ),
            ),
        )
    )


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-FLOW-03")
async def test_shortlist_normalization(monkeypatch: pytest.MonkeyPatch) -> None:
    state = _selection_state(["gneiss", "slate", "basalt", "marble"])
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "raw": AIMessage(content="", response_metadata={"finish_reason": "stop"}),
                "parsed": SelectCandidates(
                    stone_ids=[
                        "basalt",
                        "foreign",
                        "gneiss",
                        "basalt",
                        "marble",
                        "slate",
                    ]
                ),
            }
        )
    )
    monkeypatch.setattr(workflow, "structured_model", Mock(return_value=("json_schema", model)))
    monkeypatch.setattr(workflow, "get_config", lambda: {})

    result = await workflow.select_candidates(state, runtime=_selection_runtime())

    assert result["selected_stone_ids"] == ["basalt", "gneiss", "marble"]
    assert result["selection_status"] == "selected"
    assert result["selection_decisions"] == [
        {"stone_id": "gneiss", "selected": True},
        {"stone_id": "slate", "selected": False},
        {"stone_id": "basalt", "selected": True},
        {"stone_id": "marble", "selected": True},
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("finish_reason", "parsed"),
    [
        ("length", SelectCandidates(stone_ids=["gneiss"])),
        ("stop", None),
        ("stop", {"stone_ids": ["gneiss"]}),
    ],
    ids=["truncated", "missing-parsed-selection", "invalid-parsed-selection"],
)
@pytest.mark.acceptance("AC-FLOW-03")
async def test_invalid_selection_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
    finish_reason: str,
    parsed: object,
) -> None:
    state = _selection_state(["gneiss", "slate"])
    model = SimpleNamespace(
        ainvoke=AsyncMock(
            return_value={
                "raw": AIMessage(content="", response_metadata={"finish_reason": finish_reason}),
                "parsed": parsed,
            }
        )
    )
    monkeypatch.setattr(workflow, "structured_model", Mock(return_value=("json_schema", model)))
    monkeypatch.setattr(workflow, "get_config", lambda: {})

    result = await workflow.select_candidates(state, runtime=_selection_runtime())

    assert result["selection_status"] == "invalid_selection"
    assert result["selected_stone_ids"] == []
    assert result["selection_decisions"] == [
        {"stone_id": "gneiss", "selected": False},
        {"stone_id": "slate", "selected": False},
    ]
