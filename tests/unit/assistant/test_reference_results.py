"""Check mixed-result assembly and preservation of reference evidence on budget stops."""

from typing import Any

import pytest

from stone_shelter_assistant.assistant import workflow
from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceSource,
)


@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-ANSWER-01")
def test_mixed_result_keeps_both_answers_sources_and_statuses() -> None:
    candidate: dict[str, object] = {
        "answer": "Recommended companion.",
        "sources": {"stone-card:one": {"data": {"id": "one"}}},
        "verified_statuses": {"one": "AVAILABLE"},
        "recommended_stone_ids": ["one"],
        "candidate_decisions": [{"stone_id": "one", "outcome": "recommended"}],
    }
    reference: dict[str, object] = {
        "answer": "Svetlana profile. Sources: stone-card:one",
        "sources": {"stone-card:one": {"data": {"id": "different"}}, "encyclopedia:marble": {}},
        "verified_statuses": {"svetlana": "AVAILABLE"},
        "reference_answer_status": "generated",
    }
    result: Any = workflow.combine_mixed_result(candidate, reference, "generated")
    assert "Svetlana profile" in result["answer"]
    assert "Recommended companion" in result["answer"]
    assert "reference:stone-card:one" in result["answer"]
    assert "reference:stone-card:one" in result["sources"]
    assert "encyclopedia:marble" in result["sources"]
    assert result["verified_statuses"] == {"svetlana": "AVAILABLE", "one": "AVAILABLE"}
    assert result["recommended_stone_ids"] == ["one"]


@pytest.mark.acceptance("AC-FLOW-01")
@pytest.mark.acceptance("AC-ANSWER-01")
def test_budget_stop_keeps_sources_already_read_for_reference_branch() -> None:
    from stone_shelter_assistant.assistant.reference_lookup import ReferenceResult

    reference = ReferenceResult(
        lines=["No authored encyclopedia care information is available for onyx."],
        sources={"stone-card:svetlana": {"data": {"name": "Svetlana"}}},
        context_sources={
            "stone-card:svetlana": ReferenceSource(
                source_id="stone-card:svetlana", scope="individual", text="Enjoys singing."
            )
        },
    )
    stop_state: Any = {
        "question": "Tell me about Svetlana and recommend a companion.",
        "stop_reason": "budget_limit",
        "reference_result": reference,
    }
    result: Any = workflow.stop(stop_state)["result"]
    assert "No authored encyclopedia care information" in result["answer"]
    assert "Enjoys singing" in result["answer"]
    assert "stone-card:svetlana" in result["sources"]
    assert result["candidate_branch_status"] == "budget_limit"
