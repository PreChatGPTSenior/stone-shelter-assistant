"""Admission policy for pair guidance and individual compatibility evidence."""

from pathlib import Path
from uuid import UUID

import pytest

from stone_shelter_assistant.assistant.candidate_assessment import evaluate_candidate
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    SourceText,
)
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_stone_compatibility_documents,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

ROOT = Path(__file__).parents[3]
GUIDE = ROOT / "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"


def pair_by_key(key: str) -> CompatibilityPairSearchDocument:
    documents = build_stone_compatibility_documents(
        GUIDE.read_text(), "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
    )
    return next(
        item
        for item in documents
        if isinstance(item, CompatibilityPairSearchDocument) and item.pair_key == key
    )


def card(stone_type: str) -> StoneDetails:
    return StoneDetails.model_validate(
        {
            "id": str(UUID(int=801)),
            "external_id": str(UUID(int=802)),
            "name": "Fixture candidate",
            "stone_type": stone_type,
            "stone_size": "SMALL",
            "biography": None,
            "profile": None,
            "shelter_case": {
                "id": str(UUID(int=803)),
                "external_id": str(UUID(int=804)),
                "case_number": "CASE-801",
                "adoption_status": "AVAILABLE",
                "current_shelter_id": str(UUID(int=805)),
                "admission_date": "2026-01-01T00:00:00+00:00",
            },
        }
    )


def criteria(target_type: str, *, required: bool, lookup: bool = False) -> SearchCriteria:
    target = {
        "criterion_id": "requirement.compatibility.1",
        "fragment_id": 1,
        "question_quote": "Can they share a home?",
        "household_type": target_type,
    }
    return SearchCriteria.model_validate(
        {
            "recommendation_limit": 1,
            "household_facts": [],
            "requirements": {
                "character": [],
                "compatibility": [target] if required else [],
            },
            "preferences": {
                "character": [],
                "compatibility": [] if required or lookup else [target],
            },
            "requested_compatibility": [target] if lookup else [],
        }
    )


def assessment(
    stone: StoneDetails,
    pair: CompatibilityPairSearchDocument,
    *,
    finding: str,
    scope: str,
) -> tuple[CandidateEvidence, dict[str, SourceText]]:
    quote = "Needs slow introductions with this type."
    source = SourceText("profile", "stone-card:individual", "preferred_environment", quote)
    evidence = CandidateEvidence.model_validate(
        {
            "character": [],
            "individual_compatibility": [
                {
                    "stone_id": str(stone.id),
                    "pair_key": pair.pair_key,
                    "scope": scope,
                    "source_ref": "profile.preferred_environment",
                    "finding": finding,
                    "quote": quote,
                }
            ],
        }
    )
    return evidence, {"profile.preferred_environment": source}


@pytest.mark.acceptance("AC-COMPATIBILITY-01")
@pytest.mark.acceptance("AC-EVIDENCE-02")
@pytest.mark.acceptance("AC-DECISION-01")
@pytest.mark.parametrize(
    ("pair_key", "required", "lookup", "scope", "finding", "expected_eligible", "rule"),
    [
        ("GRANITE+OBSIDIAN", True, False, "cohabitation", "contradicted", False, "individual_conflict"),
        ("GRANITE+OBSIDIAN", True, False, "preference", "contradicted", True, "harmonious"),
        ("GRANITE+GRANITE", False, False, "cohabitation", "confirmed", True, "conditions_unconfirmed"),
        ("BASALT+MARBLE", True, False, "cohabitation", "confirmed", False, "not_recommended"),
        ("BASALT+MARBLE", False, True, "preference", "contradicted", True, "not_recommended"),
    ],
)
def test_pair_and_individual_conflicts(
    pair_key: str,
    required: bool,
    lookup: bool,
    scope: str,
    finding: str,
    expected_eligible: bool,
    rule: str,
) -> None:
    pair = pair_by_key(pair_key)
    candidate_type, target_type = pair_key.split("+")
    stone = card(candidate_type)
    criteria_value = criteria(target_type, required=required, lookup=lookup)
    evidence, sources = assessment(stone, pair, finding=finding, scope=scope)

    result = evaluate_candidate(
        criteria_value,
        stone,
        "AVAILABLE",
        {pair_key: pair},
        sources,
        evidence,
        "parsed",
    )

    reason = next(item for item in result.reasons if item.criterion == "compatibility")
    assert result.eligible is expected_eligible
    assert reason.policy_rule == rule
    assert reason.verdict == pair.verdict
    assert any(item.source_id == pair.source_key for item in reason.evidence)
    assert reason.chosen_evidence is not None
    if pair_key == "GRANITE+OBSIDIAN" and scope == "cohabitation":
        assert reason.chosen_evidence.source_kind == "profile"
        assert reason.conflict
    if pair_key == "GRANITE+GRANITE":
        assert reason.conditions_status == "unconfirmed"
        assert reason.chosen_evidence.source_kind == "compatibility_pair"
    if pair_key == "BASALT+MARBLE" and not lookup:
        assert "not_recommended" in result.exclusion_rules
        assert reason.chosen_evidence.source_kind == "compatibility_pair"
    if lookup:
        assert reason.lookup_only
        assert reason.action == "rank"
        assert "not_recommended" not in result.exclusion_rules
