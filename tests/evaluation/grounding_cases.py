"""Build the current typed parser input used by grounding evaluation cases."""

from collections.abc import Mapping
from typing import Any

from stone_shelter_assistant.assistant.selection import ParseQuestion


def parsed_grounding_case(case: Mapping[str, Any]) -> ParseQuestion:
    """Convert a reviewed holdout row into a source-bound current ParseQuestion."""
    question = case["question"]
    fields: dict[str, Any] = {
        "recommendation_limit": 1,
        "retrieval": {
            "lexical_query": "companion",
            "semantic_query": "a suitable companion",
        },
    }
    if case["concept_id"] == "candidate_type":
        fields["retrieval"]["candidate_type"] = {
            "fragment_id": 1,
            "stone_type": case["proposed_type"],
        }
    else:
        fields["household_facts"] = [
            {
                "fragment_id": 1,
                "question_quote": question,
                "fact_type": case["concept_id"],
                "value": case["proposed_value"],
            }
        ]
    return ParseQuestion.model_validate(fields)
