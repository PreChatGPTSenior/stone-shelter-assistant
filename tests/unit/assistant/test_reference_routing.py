"""Check mixed-reference routing and state updates directly, without running a graph."""

from typing import Any, cast

import pytest
from langgraph.runtime import Runtime

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.selection import ParseQuestion
from stone_shelter_assistant.assistant.tool_planning import (
    ToolPlan,
    permitted_tools,
)


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-QUESTION-01")
async def test_reference_and_recommendation_targets_are_explicitly_independent() -> None:
    question = "Tell me about Svetlana and find a quiet companion."
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
            "retrieval": {"lexical_query": "quiet", "semantic_query": "quiet companion"},
        }
    )
    request = parsed.resolve_references({1: question})
    assert request.stone_name == "Svetlana"
    assert request.recommendation_name is None

    same_target = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "recommendation_target": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
        }
    )
    same_request = same_target.resolve_references({1: question})
    assert same_request.stone_name == same_request.recommendation_name == "Svetlana"
    allowed = permitted_tools(parsed.resolve({1: question})[0], request)
    assert len(allowed) == 6
    mixed_state: Any = {
        "question": question,
        "tools_used": 0,
        "criteria": parsed.resolve({1: question})[0],
        "reference_request": request,
        "permitted_tools": allowed,
        "tool_plan": ToolPlan(tools=allowed, reason="Read both goals"),
        "plan_status": "accepted",
        "question_coverage_status": "complete",
        "question_fragments": {1: question},
        "result": {
            "answer": "Named individual result",
            "sources": {"individual:1": {}},
            "verified_statuses": {},
        },
    }
    assert workflow.after_planning(mixed_state) == "execute_reference_plan"
    assert workflow.after_reference_answer(mixed_state) == "mixed"
    saved: Any = await workflow.continue_mixed(
        mixed_state, runtime=Runtime(context=cast(Any, None))
    )
    assert saved["reference_component"]["answer"] == "Named individual result"

    parsed_without_name = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "requested_care": [{"fragment_id": 1, "stone_type": "OBSIDIAN"}],
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "household_type": "GRANITE",
                    "first_type": None,
                    "target": "candidate",
                }
            ],
        }
    )
    no_name_criteria, _ = parsed_without_name.resolve({1: "Find a companion; care for obsidian."})
    no_name_request = parsed_without_name.resolve_references(
        {1: "Find a companion; care for obsidian."}
    )
    no_name_plan = permitted_tools(no_name_criteria, no_name_request)
    assert no_name_plan == ["search_candidates", "search_knowledge_lexical"]
