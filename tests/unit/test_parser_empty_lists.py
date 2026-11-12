"""Empty parser collections are optional; malformed nonempty values are not."""

import pytest
from pydantic import ValidationError

from stone_shelter_assistant.assistant.selection import CriterionReference, ParseQuestion


def test_missing_preference_list_is_empty_without_losing_requirements() -> None:
    parsed = ParseQuestion.model_validate(
        {
            "recommendation_limit": 3,
            "requirements": {
                "character": [
                    {"fragment_id": 1, "question_quote": "stay quiet in the early morning"}
                ]
            },
            "preferences": {"character": []},
            "retrieval": {
                "lexical_query": "quiet morning",
                "semantic_query": "a quiet morning companion",
            },
        }
    )
    criteria, _ = parsed.resolve({1: "The stone must stay quiet in the early morning."})
    assert criteria.preferences.character == criteria.preferences.compatibility == []
    assert criteria.requirements.compatibility == []
    assert criteria.requirements.character[0].fragment_id == 1
    assert (
        parsed.resolve_retrieval({1: "The stone must stay quiet in the early morning."}) is not None
    )


def test_optional_groups_and_lists_do_not_share_mutable_defaults() -> None:
    first = ParseQuestion(recommendation_limit=1)
    second = ParseQuestion(recommendation_limit=1)
    first.preferences.character.append(
        CriterionReference(fragment_id=1, question_quote="quiet")
    )
    assert second.preferences.character == []
    criteria, _ = second.resolve({})
    assert criteria.household_facts == criteria.requested_availability == []


@pytest.mark.parametrize("field", ["character", "compatibility"])
def test_null_list_is_not_silently_treated_as_empty(field: str) -> None:
    with pytest.raises(ValidationError):
        ParseQuestion.model_validate({"recommendation_limit": 1, "preferences": {field: None}})


def test_invalid_nonempty_reference_remains_invalid() -> None:
    with pytest.raises(ValidationError):
        ParseQuestion.model_validate(
            {"recommendation_limit": 1, "requirements": {"character": [{"fragment_id": 0}]}}
        )
