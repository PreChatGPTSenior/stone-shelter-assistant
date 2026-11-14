from datetime import UTC, datetime
from typing import Literal
from uuid import UUID

import pytest

from stone_shelter_assistant.assistant.candidate_assessment import evaluate_candidate
from stone_shelter_assistant.assistant.candidate_criteria import (
    CriteriaGroup,
    QuotedCriterion,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    CharacterFinding,
    SourceText,
)
from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    StoneSize,
    StoneType,
)
from stone_shelter_assistant.stones.stone_contracts import (
    ShelterCaseDetails,
    StoneDetails,
    StoneProfileDetails,
)


@pytest.mark.acceptance("AC-DECISION-01")
@pytest.mark.parametrize(
    ("finding", "eligible", "exclusion_rules"),
    [
        ("confirmed", True, []),
        ("contradicted", False, ["requirement_not_met"]),
        (None, False, ["requirement_not_met"]),
    ],
)
def test_required_and_preferred_findings(
    finding: Literal["confirmed", "contradicted"] | None,
    eligible: bool,
    exclusion_rules: list[str],
) -> None:
    quote = "Enjoys a quiet home."
    requirement = QuotedCriterion(
        criterion_id="requirement.quiet", fragment_id=1, question_quote=quote
    )
    preference = QuotedCriterion(
        criterion_id="preference.quiet", fragment_id=2, question_quote=quote
    )
    criteria = SearchCriteria(
        recommendation_limit=1,
        household_facts=[],
        requirements=CriteriaGroup(character=[requirement], compatibility=[]),
        preferences=CriteriaGroup(character=[preference], compatibility=[]),
    )
    card = StoneDetails(
        id=UUID("00000000-0000-0000-0000-000000000001"),
        external_id=UUID("00000000-0000-0000-0000-000000000002"),
        name="Quiet Stone",
        stone_type=StoneType.GRANITE,
        stone_size=StoneSize.MEDIUM,
        biography=None,
        profile=StoneProfileDetails(
            socialization_traits=[],
            care_level=None,
            health_notes=None,
            trigger_notes=None,
            preferred_environment=quote,
        ),
        shelter_case=ShelterCaseDetails(
            id=UUID("00000000-0000-0000-0000-000000000003"),
            external_id=UUID("00000000-0000-0000-0000-000000000004"),
            case_number="TEST-1",
            adoption_status=AdoptionStatus.AVAILABLE,
            current_shelter_id=UUID("00000000-0000-0000-0000-000000000005"),
            admission_date=datetime(2026, 1, 1, tzinfo=UTC),
        ),
    )
    sources = {
        "profile.preferred_environment": SourceText(
            "profile", "stone-card:test", "preferred_environment", quote
        )
    }
    findings = (
        [
            CharacterFinding(
                stone_id=str(card.id),
                source_ref="profile.preferred_environment",
                finding=finding,
                quote=quote,
                criterion_id=criterion_id,
                fragment_id=fragment_id,
            )
            for criterion_id, fragment_id in (("requirement.quiet", 1), ("preference.quiet", 2))
        ]
        if finding is not None
        else []
    )
    evaluation = evaluate_candidate(
        criteria,
        card,
        AdoptionStatus.AVAILABLE,
        {},
        sources,
        CandidateEvidence(character=findings, individual_compatibility=[]),
        "parsed",
    )

    reasons = {reason.criterion_id: reason for reason in evaluation.reasons if reason.criterion_id}
    assert reasons["requirement.quiet"].finding == (finding or "unknown")
    assert reasons["preference.quiet"].finding == (finding or "unknown")
    assert evaluation.eligible is eligible
    assert evaluation.exclusion_rules == exclusion_rules

    preference_only = criteria.model_copy(
        update={
            "requirements": CriteriaGroup(character=[], compatibility=[]),
            "preferences": CriteriaGroup(character=[preference], compatibility=[]),
        }
    )
    preference_evaluation = evaluate_candidate(
        preference_only,
        card,
        AdoptionStatus.AVAILABLE,
        {},
        sources,
        CandidateEvidence(character=findings, individual_compatibility=[]),
        "parsed",
    )
    assert preference_evaluation.eligible is True
    assert preference_evaluation.exclusion_rules == []
