"""Checks for the fixed candidate-evidence comparison fixture.

Validates quoted evidence and criterion coverage, applies the real candidate
policy, and exposes Langfuse check scores. Used by isolated assessment evaluation
and unit tests; these deterministic checks do not judge arbitrary answer meaning.
"""

import json
from typing import Any

from langfuse import Evaluation

from stone_shelter_assistant.assistant.candidate_assessment import evaluate_candidate
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import (
    CandidateEvidence,
    candidate_sources,
)
from stone_shelter_assistant.search.document_models import (
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

CHECKS = ("dto_valid", "evidence_grounded", "character_coverage", "no_invented_compatibility")


def check_assessment(assessment: CandidateEvidence, snapshot: dict[str, Any]) -> dict[str, Any]:
    """Check source grounding and the explicit facts of this frozen scenario."""
    criteria = SearchCriteria.model_validate(snapshot["criteria"])
    cards = [StoneDetails.model_validate(value) for value in snapshot["cards"]]
    documents = snapshot["documents"].values()
    chapters = {
        value["stone_types"][0]: EncyclopediaSectionSearchDocument.model_validate(value)
        for value in documents
        if value.get("document_kind") == "encyclopedia_section"
    }
    pairs = {
        value["pair_key"]: CompatibilityPairSearchDocument.model_validate(value)
        for value in snapshot["documents"].values()
        if value.get("document_kind") == "compatibility_pair"
    }
    sources = json.loads(snapshot["messages"][1]["content"])["candidate_sources"]
    supplied = {(item["stone_id"], item["source_ref"]): item["text"] for item in sources}
    criterion_fragments = {
        criterion.criterion_id: criterion.fragment_id
        for criterion in (*criteria.requirements.character, *criteria.preferences.character)
    }
    grounded = all(
        (finding.stone_id, finding.source_ref) in supplied
        and finding.quote in supplied[(finding.stone_id, finding.source_ref)]
        for finding in (*assessment.character, *assessment.individual_compatibility)
    ) and all(
        finding.criterion_id in criterion_fragments
        and finding.fragment_id == criterion_fragments[finding.criterion_id]
        for finding in assessment.character
    )
    covered = {
        (finding.stone_id, finding.criterion_id)
        for finding in assessment.character
        if finding.finding == "confirmed"
        and finding.criterion_id in criterion_fragments
        and finding.fragment_id == criterion_fragments[finding.criterion_id]
    }
    expected_coverage = {
        (str(card.id), criterion_id) for card in cards for criterion_id in criterion_fragments
    }
    evaluations = [
        evaluate_candidate(
            criteria,
            card,
            snapshot["verified_statuses"][str(card.id)],
            pairs,
            candidate_sources(card, chapters.get(card.stone_type)),
            assessment,
            "parsed",
        ).model_dump(mode="json")
        for card in cards
    ]
    # Both biographies explicitly describe quiet/peaceful homes. Neither card states
    # a preference for granite, and no household fact establishes conditional arrangements.
    return {
        "dto_valid": True,
        "evidence_grounded": grounded,
        "character_coverage": covered == expected_coverage,
        "no_invented_compatibility": not assessment.individual_compatibility,
        "candidate_evaluations": evaluations,
        "assessment": assessment.model_dump(mode="json"),
    }


def score_checks(*, output: Any, **kwargs: Any) -> list[Evaluation]:
    return [Evaluation(name=name, value=float(bool(output.get(name)))) for name in CHECKS]
