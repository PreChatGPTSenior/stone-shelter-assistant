"""Prepare grounding evaluation cases and summarize their measured outcomes.

parsed_grounding_case builds a ParseQuestion for one holdout row, representing
either a requested candidate type or a household agreement with its source
fragment. Grounding evaluation and unit tests pass these proposals to the real
verifier. grounding_metrics compares expected and observed classifications;
this module does not run a model, choose expected verdicts, or implement a
legacy parser.
"""

from collections.abc import Mapping
from typing import Any

from stone_shelter_assistant.assistant.selection import ParseQuestion


def parsed_grounding_case(case: Mapping[str, Any]) -> ParseQuestion:
    """Convert a reviewed holdout row into a source-bound current ParseQuestion."""
    question = case["question"]
    is_candidate_type = case["concept_id"] == "candidate_type"
    fields: dict[str, Any] = {
        "recommendation_limit": 1 if is_candidate_type else 0,
    }
    if is_candidate_type:
        fields["retrieval"] = {
            "lexical_query": "companion",
            "semantic_query": "a suitable companion",
            "candidate_type": {
                "fragment_id": 1,
                "stone_type": case["proposed_type"],
            },
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


def grounding_metrics(
    expected: list[str], actual: list[str | None]
) -> dict[str, float | int | None]:
    """Summarize aligned expected and observed grounding classifications."""
    if not expected or len(expected) != len(actual):
        raise ValueError("Expected aligned, nonempty measurements")
    positives = sum(value == "supported" for value in actual)
    true_positive = sum(e == a == "supported" for e, a in zip(expected, actual, strict=True))
    return {
        "count": len(expected),
        "technical_failures": sum(value is None for value in actual),
        "classification_accuracy": sum(e == a for e, a in zip(expected, actual, strict=True))
        / len(expected),
        "acceptance_accuracy": sum(
            a is not None and (e == "supported") == (a == "supported")
            for e, a in zip(expected, actual, strict=True)
        )
        / len(expected),
        "false_acceptances": sum(
            a == "supported" and e != "supported" for e, a in zip(expected, actual, strict=True)
        ),
        "supported_precision": true_positive / positives if positives else None,
    }
