"""Check exact reference quotations and citation scope validation."""

import pytest

from stone_shelter_assistant.assistant.reference_evidence import (
    ReferenceAnswer,
    ReferenceEvidence,
    ReferenceSection,
    ReferenceSource,
    check_reference_quotes,
    reference_citations_valid,
)


@pytest.mark.acceptance("AC-EVIDENCE-01")
@pytest.mark.acceptance("AC-EVIDENCE-02")
@pytest.mark.acceptance("AC-ANSWER-01")
def test_reference_evidence_rejects_invented_quotes_and_cross_scope_citations() -> None:
    sources = {
        "one": ReferenceSource(source_id="one", scope="encyclopedia", text="General type traits.")
    }
    evidence = ReferenceEvidence.model_validate(
        {
            "quotes": [
                {"source_id": "one", "quote": "General type traits."},
                {"source_id": "one", "quote": "Invented individual preference."},
                {"source_id": "missing", "quote": "General type traits."},
            ]
        }
    )
    accepted, rejected = check_reference_quotes(evidence, sources)
    assert len(accepted) == 1 and accepted[0].scope == "encyclopedia"
    assert {r["reason"] for r in rejected} == {"non_verbatim_quote", "unknown_source_ref"}
    answer = ReferenceAnswer(
        sections=[
            ReferenceSection(
                scope="individual", explanation="Individual preference", source_ids=["one"]
            )
        ]
    )
    assert not reference_citations_valid(answer, accepted)
