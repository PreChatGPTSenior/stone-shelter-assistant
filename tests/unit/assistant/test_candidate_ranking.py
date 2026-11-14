from typing import Literal

import pytest

from stone_shelter_assistant.assistant.candidate_assessment import (
    CandidateEvaluation,
    Outcome,
    Reason,
)
from stone_shelter_assistant.assistant.candidate_criteria import CriteriaGroup, SearchCriteria
from stone_shelter_assistant.assistant.candidate_evidence import Evidence
from stone_shelter_assistant.assistant.candidate_ranking import (
    calculate_ranking,
    recommendation_order,
)


def scored_reason(
    criterion: Literal["availability", "character", "compatibility"],
    score: float,
    *,
    source_kind: Literal["profile", "observation", "biography", "encyclopedia", "compatibility_pair"]
    | None = None,
    lookup_only: bool = False,
    action: Literal["rank", "conditional_option", "exclude"] = "rank",
) -> Reason:
    source = (
        Evidence(
            source_id=f"source-{source_kind}",
            field="test",
            source_kind=source_kind,
            priority=1,
            weight={"profile": 1.0, "observation": 0.95, "compatibility_pair": 1.0}[source_kind],
            supports_requirement=True,
            finding="confirmed",
        )
        if source_kind
        else None
    )
    return Reason(
        criterion=criterion,
        finding="confirmed",
        required=False,
        policy_rule="test",
        base_score=score,
        chosen_evidence=source,
        lookup_only=lookup_only,
        action=action,
    )


def evaluation(
    stone_id: str,
    external_id: str,
    reasons: list[Reason],
    *,
    eligible: bool = True,
) -> CandidateEvaluation:
    return CandidateEvaluation(
        stone_id=stone_id,
        external_id=external_id,
        eligible=eligible,
        reasons=reasons,
        exclusion_rules=[] if eligible else ["test_exclusion"],
    )


@pytest.mark.acceptance("AC-DECISION-01")
def test_score_aggregation() -> None:
    candidate = evaluation(
        "stone-1",
        "external-1",
        [
            scored_reason("compatibility", 0.8, source_kind="compatibility_pair"),
            scored_reason("compatibility", 0.4, source_kind="profile"),
            scored_reason("character", 1.0, source_kind="observation"),
            scored_reason("character", 0.5, source_kind="profile"),
            scored_reason("compatibility", 0.0, lookup_only=True),
        ],
    )

    result = calculate_ranking(candidate, include_lookups=False)

    # Compatibility is min(0.8, 0.4); character is mean(1.0 * .95, .5 * 1.0).
    # Active policy weights .60/.40 are already normalized across both groups.
    assert result.criteria["compatibility"].score == pytest.approx(0.4)
    assert result.criteria["compatibility"].effective_weight == pytest.approx(0.6)
    assert [item.source_weight for item in result.criteria["character"].reasons] == [0.95, 1.0]
    assert result.criteria["character"].aggregation == "mean"
    assert result.criteria["character"].score == pytest.approx(0.725)
    assert result.criteria["character"].effective_weight == pytest.approx(0.4)
    assert result.total == pytest.approx(0.53)

    lookup_only = evaluation("stone-2", "external-2", [scored_reason(
        "compatibility", 1.0, lookup_only=True
    )])
    assert calculate_ranking(lookup_only, include_lookups=False).total is None
    assert calculate_ranking(lookup_only, include_lookups=True).total == pytest.approx(1.0)


def criteria(limit: int) -> SearchCriteria:
    return SearchCriteria(
        recommendation_limit=limit,
        household_facts=[],
        requirements=CriteriaGroup(character=[], compatibility=[]),
        preferences=CriteriaGroup(character=[], compatibility=[]),
    )


@pytest.mark.acceptance("AC-DECISION-01")
def test_order_ties_and_limit() -> None:
    prepared = [
        # This lower compatibility score still wins on total (.76 versus .70).
        evaluation(
            "total-wins",
            "Y",
            [scored_reason("character", 1.0), scored_reason("compatibility", 0.6)],
        ),
        # Both candidates total .70. Compatibility wins despite the opposing external-ID order.
        evaluation(
            "compatibility-wins",
            "Z",
            [scored_reason("character", 0.55), scored_reason("compatibility", 0.8)],
        ),
        evaluation(
            "compatibility-loses",
            "A",
            [scored_reason("character", 1.0), scored_reason("compatibility", 0.5)],
        ),
        # These tie on score and compatibility; external IDs oppose their internal IDs.
        evaluation(
            "z-internal",
            "B",
            [scored_reason("character", 0.7), scored_reason("compatibility", 0.7)],
        ),
        evaluation(
            "a-internal",
            "C",
            [scored_reason("character", 0.7), scored_reason("compatibility", 0.7)],
        ),
        evaluation("d", "D", [scored_reason("character", 0.5)], eligible=False),
        evaluation(
            "e",
            "E",
            [
                scored_reason("character", 1.0),
                scored_reason("compatibility", 1.0, action="conditional_option"),
            ],
        ),
    ]

    def order(
        items: list[CandidateEvaluation],
    ) -> tuple[list[str], dict[str, tuple[int | None, Outcome]]]:
        selected = recommendation_order(items, criteria(3))
        states = {
            item.stone_id: (item.ranking.rank if item.ranking else None, item.outcome)
            for item in items
        }
        return selected, states

    expected = (
        ["total-wins", "compatibility-wins", "z-internal"],
        {
            "total-wins": (1, "recommended"),
            "compatibility-wins": (2, "recommended"),
            "compatibility-loses": (5, "eligible_over_limit"),
            "z-internal": (3, "recommended"),
            "a-internal": (4, "eligible_over_limit"),
            "d": (None, "excluded"),
            "e": (None, "conditional_option"),
        },
    )
    assert order(prepared) == expected
    assert order(list(reversed(prepared))) == expected
