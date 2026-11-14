"""Check typed reference targets and tool-plan dependency rules."""

from typing import Any

import pytest

from stone_shelter_assistant.assistant.selection import ParseQuestion
from stone_shelter_assistant.assistant.tool_planning import (
    ToolPlan,
    permitted_tools,
    plan_error,
)


@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-QUESTION-01")
@pytest.mark.acceptance("AC-IDENTITY-01")
def test_named_overview_requires_identity_and_card_before_type_knowledge() -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 0,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "overview"},
        }
    )
    criteria, _ = parsed.resolve({1: "Tell me about Svetlana."})
    request = parsed.resolve_references({1: "Tell me about Svetlana."})
    allowed = permitted_tools(criteria, request)
    assert (
        plan_error(ToolPlan(tools=allowed, reason="Read identity before type"), allowed, request)
        is None
    )
    bad = [allowed[0], allowed[3], allowed[1], *allowed[2:3], *allowed[4:]]
    assert (
        plan_error(ToolPlan(tools=bad, reason="Wrong dependency order"), allowed, request)
        == "stone_card_must_be_read_before_type_knowledge"
    )
    mixed_criteria = criteria.model_copy(update={"recommendation_limit": 1})
    mixed_allowed = permitted_tools(mixed_criteria, request)
    assert "search_candidates" in mixed_allowed
    assert "get_stone_details" in mixed_allowed
    assert (
        plan_error(
            ToolPlan(tools=mixed_allowed, reason="Cover both requested branches"),
            mixed_allowed,
            request,
        )
        is None
    )


@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-QUESTION-01")
@pytest.mark.acceptance("AC-IDENTITY-01")
def test_explicit_named_availability_question_keeps_status_lookup_route() -> None:
    question = "Is Madame Obsidian available?"
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 0,
            "requested_availability": [{"fragment_id": 1}],
            "named_stone": {"fragment_id": 1, "name": "Madame Obsidian"},
        }
    )

    criteria, _ = parsed.resolve({1: question})
    request = parsed.resolve_references({1: question})

    assert permitted_tools(criteria, request) == ["get_stone_status_by_name"]


@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-QUESTION-01")
@pytest.mark.acceptance("AC-IDENTITY-01")
def test_candidate_compatibility_does_not_become_named_reference_pair() -> None:
    fragments = {
        1: "What does Svetlana like?",
        2: "Recommend one quiet companion compatible with granite.",
    }
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 1,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_stone_info": {"fragment_id": 1, "topic": "preferences"},
            "requested_compatibility": [
                {
                    "fragment_id": 2,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "candidate",
                }
            ],
        }
    )
    criteria, _ = parsed.resolve(fragments)
    request = parsed.resolve_references(fragments)
    assert not request.pairs
    assert criteria.requested_compatibility[0].household_type.value == "GRANITE"
    parsed_reference_pair = ParseQuestion.model_validate(
        {
            **parsed.model_dump(),
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        }
    )
    assert (
        parsed_reference_pair.resolve_references(fragments).pairs[0].second_type.value == "GRANITE"
    )
    invalid_cases: list[dict[str, Any]] = [
        {
            "recommendation_limit": 0,
            "named_stone": {"fragment_id": 1, "name": "Svetlana"},
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": "BASALT",
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "types",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 999,
                    "first_type": "BASALT",
                    "household_type": "GRANITE",
                    "target": "types",
                }
            ],
        },
        {
            "recommendation_limit": 0,
            "requested_compatibility": [
                {
                    "fragment_id": 1,
                    "first_type": None,
                    "household_type": "GRANITE",
                    "target": "named_stone",
                }
            ],
        },
    ]
    for fields in invalid_cases:
        with pytest.raises((KeyError, ValueError)):
            ParseQuestion.model_validate(fields).resolve_references(fragments)
