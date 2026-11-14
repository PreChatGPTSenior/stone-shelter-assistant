"""Regressions for invalid references without model calls."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from stone_shelter_assistant.assistant.candidate_assessment import (
    character_reasons,
    evaluate_candidate,
)
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    SourceText,
    assessment_failure_status,
)
from stone_shelter_assistant.search.document_models import EncyclopediaSectionSearchDocument
from stone_shelter_assistant.search.knowledge.encyclopedia_document_builder import (
    build_encyclopedia_documents,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

FIXTURE = Path(__file__).parents[3] / "fixtures/assistant/quiet-home-assessment.json"
ROOT = Path(__file__).parents[3]


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_uuid_source_ref_is_rejected_and_classified_through_parser_wrapper() -> None:
    with pytest.raises(ValidationError) as caught:
        CandidateEvidence.model_validate(
            {
                "character": [
                    {
                        "stone_id": "candidate",
                        "criterion_id": "preference.character.1",
                        "source_ref": "d484c7c8-9bf9-47bf-8b45-34a8db1f1b60",
                        "finding": "confirmed",
                        "quote": "enjoys quiet evenings",
                        "fragment_id": 1,
                    }
                ],
                "individual_compatibility": [],
            }
        )
    assert assessment_failure_status(caught.value) == "invalid_source_ref"
    wrapper = ValueError("Structured output parsing failed")
    wrapper.__cause__ = caught.value
    assert assessment_failure_status(wrapper) == "invalid_source_ref"


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_other_validation_errors_are_not_source_reference_errors() -> None:
    with pytest.raises(ValidationError) as caught:
        CandidateEvidence.model_validate({"character": [], "individual_compatibility": None})
    assert assessment_failure_status(caught.value) == "invalid_response"
    assert assessment_failure_status(None) == "invalid_response"


@pytest.mark.parametrize(
    ("ref", "quote", "expected"),
    [
        ("biography", "enjoys quiet evenings", None),
        ("profile.trigger_notes", "enjoys quiet evenings", "invalid_source_ref"),
        ("biography", "loves loud parties", "missing_evidence"),
    ],
)
@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_reference_presence_and_quote_support_are_separate(
    ref: str, quote: str, expected: str | None
) -> None:
    snapshot = json.loads(FIXTURE.read_text())
    criteria = SearchCriteria.model_validate(snapshot["criteria"])
    output = {
        "character": [
            {
                "stone_id": "candidate",
                "criterion_id": "preference.character.1",
                "fragment_id": 1,
                "finding": "confirmed",
                "source_ref": ref,
                "quote": quote,
            }
        ],
        "individual_compatibility": [],
    }
    finding = output["character"][0]
    finding.update(source_ref=ref, quote=quote)
    assessment = CandidateEvidence.model_validate(output)
    reasons = character_reasons(
        assessment.character[0].stone_id,
        criteria,
        {
            "biography": SourceText(
                "biography", "card", "biography", "A thoughtful stone who enjoys quiet evenings."
            )
        },
        assessment,
        "parsed",
    )
    assert reasons[0].unknown_reason == expected
    assert reasons[0].finding == ("confirmed" if expected is None else "unknown")


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_schema_rejection_remains_visible_in_candidate_reason() -> None:
    snapshot = json.loads(FIXTURE.read_text())
    reasons = character_reasons(
        "candidate",
        SearchCriteria.model_validate(snapshot["criteria"]),
        {},
        CandidateEvidence(character=[], individual_compatibility=[]),
        "invalid_source_ref",
    )
    assert reasons[0].unknown_reason == "invalid_source_ref"


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_two_required_atoms_in_one_fragment_need_separate_findings() -> None:
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [],
            "requirements": {
                "character": [
                    {
                        "criterion_id": "requirement.character.1",
                        "fragment_id": 1,
                        "question_quote": "thoughtful",
                    },
                    {
                        "criterion_id": "requirement.character.2",
                        "fragment_id": 1,
                        "question_quote": "quiet evenings",
                    },
                ],
                "compatibility": [],
            },
            "preferences": {"character": [], "compatibility": []},
        }
    )
    sources = {
        "biography": SourceText(
            "biography",
            "stone-card:candidate",
            "biography",
            "A thoughtful stone who enjoys quiet evenings.",
        )
    }

    def finding(criterion_id: str, quote: str) -> dict[str, object]:
        return {
            "stone_id": "candidate",
            "criterion_id": criterion_id,
            "fragment_id": 1,
            "source_ref": "biography",
            "finding": "confirmed",
            "quote": quote,
        }

    one_finding = CandidateEvidence.model_validate(
        {
            "character": [finding("requirement.character.1", "thoughtful")],
            "individual_compatibility": [],
        }
    )
    one_reason_each = character_reasons("candidate", criteria, sources, one_finding, "parsed")
    assert [(reason.criterion_id, reason.finding) for reason in one_reason_each] == [
        ("requirement.character.1", "confirmed"),
        ("requirement.character.2", "unknown"),
    ]
    assert one_reason_each[1].unknown_reason == "missing_evidence"

    both_findings = CandidateEvidence.model_validate(
        {
            "character": [
                finding("requirement.character.1", "thoughtful"),
                finding("requirement.character.2", "quiet evenings"),
            ],
            "individual_compatibility": [],
        }
    )
    both_reasons = character_reasons("candidate", criteria, sources, both_findings, "parsed")
    assert [reason.finding for reason in both_reasons] == ["confirmed", "confirmed"]


@pytest.mark.parametrize(
    ("include_profile", "expected_source"),
    [(True, "profile"), (False, "observation")],
)
@pytest.mark.acceptance("AC-EVIDENCE-01")
@pytest.mark.acceptance("AC-EVIDENCE-02")
def test_authoritative_profile_and_observations_rank_before_biography(
    include_profile: bool, expected_source: str
) -> None:
    event_id = "94156b7f-cc92-4d65-861e-bd87e8662fb5"
    sources = {
        "biography": SourceText(
            "biography", "stone-card:candidate", "biography", "Sings quietly in the morning."
        ),
        f"observation:{event_id}": SourceText(
            "observation",
            f"case-event:{event_id}",
            "event_notes",
            "Staff observed loud singing at 05:00.",
            event_external_id=event_id,
            event_type="OBSERVATION",
            occurred_at="2026-11-02T05:00:00+04:00",
        ),
    }
    if include_profile:
        sources["profile.preferred_environment"] = SourceText(
            "profile",
            "stone-card:candidate",
            "preferred_environment",
            "Quiet mornings are preferred.",
        )
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [],
            "requirements": {
                "character": [
                    {
                        "criterion_id": "requirement.character.1",
                        "fragment_id": 1,
                        "question_quote": "Must stay quiet.",
                    }
                ],
                "compatibility": [],
            },
            "preferences": {"character": [], "compatibility": []},
        }
    )
    findings = [
        {
            "stone_id": "candidate",
            "criterion_id": "requirement.character.1",
            "fragment_id": 1,
            "source_ref": "biography",
            "observation_external_id": "94156b7f-cc92-4d65-861e-bd87e8662fb5",
            "finding": "confirmed",
            "quote": "Sings quietly in the morning.",
        },
        {
            "stone_id": "candidate",
            "criterion_id": "requirement.character.1",
            "fragment_id": 1,
            "source_ref": "observation",
            "observation_external_id": event_id,
            "finding": "contradicted",
            "quote": "loud singing at 05:00",
        },
    ]
    if include_profile:
        findings.append(
            {
                "stone_id": "candidate",
                "criterion_id": "requirement.character.1",
                "fragment_id": 1,
                "source_ref": "profile.preferred_environment",
                "finding": "confirmed",
                "quote": "Quiet mornings are preferred.",
            }
        )
    assessment = CandidateEvidence.model_validate(
        {"character": findings, "individual_compatibility": []}
    )
    reason = character_reasons("candidate", criteria, sources, assessment, "parsed")[0]
    assert reason.chosen_evidence is not None
    assert reason.chosen_evidence.source_kind == expected_source
    assert {item.source_kind for item in reason.evidence} == {
        "biography",
        "observation",
        *({"profile"} if include_profile else set()),
    }
    assert reason.conflict
    event_evidence = next(item for item in reason.evidence if item.source_kind == "observation")
    assert event_evidence.source_id == f"case-event:{event_id}"
    assert sources[f"observation:{event_id}"].occurred_at == "2026-11-02T05:00:00+04:00"


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_observation_external_id_must_match_an_authoritative_event() -> None:
    snapshot = json.loads(FIXTURE.read_text())
    criteria = SearchCriteria.model_validate(snapshot["criteria"])
    assessment = CandidateEvidence.model_validate(
        {
            "character": [
                {
                    "stone_id": "candidate",
                    "criterion_id": "preference.character.1",
                    "fragment_id": 1,
                    "source_ref": "observation",
                    "observation_external_id": "94156b7f-cc92-4d65-861e-bd87e8662fb5",
                    "finding": "confirmed",
                    "quote": "a quote from an event",
                }
            ],
            "individual_compatibility": [],
        }
    )
    reason = character_reasons("candidate", criteria, {}, assessment, "parsed")[0]
    assert reason.unknown_reason == "invalid_source_ref"
    assert reason.finding == "unknown"


@pytest.mark.acceptance("AC-EVIDENCE-01")
def test_observation_source_requires_an_event_external_id() -> None:
    with pytest.raises(ValidationError) as caught:
        CandidateEvidence.model_validate(
            {
                "character": [
                    {
                        "stone_id": "candidate",
                        "criterion_id": "requirement.character.1",
                        "fragment_id": 1,
                        "source_ref": "observation",
                        "finding": "confirmed",
                        "quote": "An event observation.",
                    }
                ],
                "individual_compatibility": [],
            }
        )
    assert assessment_failure_status(caught.value) == "invalid_source_ref"


@pytest.mark.acceptance("AC-EVIDENCE-02")
@pytest.mark.acceptance("AC-DECISION-01")
def test_type_evidence_cannot_prove_individual_requirement() -> None:
    snapshot = json.loads(FIXTURE.read_text())
    card_data = next(item for item in snapshot["cards"] if item["stone_type"] == "GRANITE")
    card = StoneDetails.model_validate(card_data)
    quote = "Granite is the character who writes everything down, labels the spare key"
    encyclopedia = next(
        item
        for item in build_encyclopedia_documents(
            (ROOT / "fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md").read_text(),
            "fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md",
        )
        if isinstance(item, EncyclopediaSectionSearchDocument)
        and item.source_key == "encyclopedia:en:granite"
    )
    source_id = encyclopedia.source_key
    sources = {
        "encyclopedia": SourceText(
            "encyclopedia", source_id, "section", encyclopedia.text
        )
    }
    criteria = SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [],
            "requirements": {
                "character": [{
                    "criterion_id": "requirement.character.1",
                    "fragment_id": 1,
                    "question_quote": "Must be organized.",
                }],
                "compatibility": [],
            },
            "preferences": {
                "character": [{
                    "criterion_id": "preference.character.1",
                    "fragment_id": 2,
                    "question_quote": "Would prefer an organized type.",
                }],
                "compatibility": [],
            },
        }
    )
    evidence = CandidateEvidence.model_validate(
        {
            "character": [
                {
                    "stone_id": str(card.id),
                    "criterion_id": criterion,
                    "fragment_id": fragment,
                    "source_ref": "encyclopedia",
                    "finding": "confirmed",
                    "quote": quote,
                }
                for criterion, fragment in (
                    ("requirement.character.1", 1),
                    ("preference.character.1", 2),
                )
            ],
            "individual_compatibility": [],
        }
    )

    result = evaluate_candidate(criteria, card, "AVAILABLE", {}, sources, evidence, "parsed")
    requirement, preference = [r for r in result.reasons if r.criterion == "character"]
    assert requirement.finding == "unknown"
    assert requirement.unknown_reason == "missing_evidence"
    assert requirement.evidence[0].source_id == source_id
    assert requirement.evidence[0].supports_requirement is False
    assert preference.finding == "confirmed"
    assert preference.chosen_evidence is not None
    assert preference.chosen_evidence.weight == 0.5
    assert not result.eligible
    assert "requirement_not_met" in result.exclusion_rules
