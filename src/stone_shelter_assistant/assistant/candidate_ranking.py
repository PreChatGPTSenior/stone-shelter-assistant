"""Calculate candidate scores and final recommendation order."""

from stone_shelter_assistant.assistant.candidate_assessment import (
    CandidateEvaluation,
    CriterionScore,
    RankingCalculation,
    ScoredReason,
)
from stone_shelter_assistant.assistant.candidate_criteria import SearchCriteria
from stone_shelter_assistant.assistant.ranking_policy import RANKING_POLICY, Criterion


def calculate_ranking(
    candidate: CandidateEvaluation, *, include_lookups: bool
) -> RankingCalculation:
    """Keep the score, source multiplier, and normalized contribution for each criterion."""
    groups: dict[Criterion, list[ScoredReason]] = {}
    for criterion in RANKING_POLICY.criteria:
        for reason in candidate.reasons:
            if (
                reason.criterion != criterion
                or reason.base_score is None
                or (reason.lookup_only and not include_lookups)
            ):
                continue
            source = reason.chosen_evidence
            weight = source.weight if source else RANKING_POLICY.missing_source_weight
            groups.setdefault(criterion, []).append(
                ScoredReason(
                    rule=reason.policy_rule,
                    question_quote=reason.question_quote,
                    source_id=source.source_id if source else None,
                    base_score=reason.base_score,
                    source_weight=weight,
                    adjusted_score=reason.base_score * weight,
                )
            )
    total_weight = sum(RANKING_POLICY.criteria[criterion].weight for criterion in groups)
    scores = {}
    for criterion, reasons in groups.items():
        rule = RANKING_POLICY.criteria[criterion]
        values = [reason.adjusted_score for reason in reasons]
        match rule.aggregation:
            case "minimum":
                score = min(values)
            case "maximum":
                score = max(values)
            case "mean":
                score = sum(values) / len(values)
        effective_weight = rule.weight / total_weight if total_weight else 0.0
        scores[criterion] = CriterionScore(
            aggregation=rule.aggregation,
            weight=rule.weight,
            effective_weight=effective_weight,
            score=score,
            contribution=score * effective_weight,
            reasons=reasons,
        )
    tie_break_values: dict[str, float | str] = {"external_id": candidate.external_id}
    tie_break_values.update(
        (criterion, round(score.score, RANKING_POLICY.score_precision))
        for criterion, score in scores.items()
    )
    return RankingCalculation(
        criteria=scores,
        total=round(
            sum(score.contribution for score in scores.values()), RANKING_POLICY.score_precision
        )
        if total_weight
        else None,
        tie_break_values={
            rule.field: tie_break_values.get(rule.field, RANKING_POLICY.missing_tie_break_score)
            for rule in RANKING_POLICY.candidate_tie_breaks
        },
    )


def candidate_score(candidate: CandidateEvaluation) -> float:
    calculation = candidate.ranking
    assert calculation is not None
    return (
        calculation.total
        if calculation.total is not None
        else RANKING_POLICY.missing_tie_break_score
    )


def candidate_tie_break(candidate: CandidateEvaluation, field: str) -> float | str:
    calculation = candidate.ranking
    assert calculation is not None
    return calculation.tie_break_values[field]


def recommendation_order(
    evaluations: list[CandidateEvaluation], criteria: SearchCriteria | None
) -> list[str]:
    """Set a disposition and a calculation for every candidate."""
    for candidate in evaluations:
        candidate.ranking = calculate_ranking(
            candidate, include_lookups=criteria is not None and criteria.recommendation_limit == 0
        )
    if criteria is None:
        for candidate in evaluations:
            candidate.outcome = "criteria_unavailable"
        return []
    if criteria.recommendation_limit == 0:
        return []

    ranked = []
    for candidate in evaluations:
        if not candidate.eligible:
            candidate.outcome = "excluded"
        elif any(reason.action == "conditional_option" for reason in candidate.reasons):
            candidate.outcome = "conditional_option"
        else:
            candidate.outcome = "eligible_over_limit"
            ranked.append(candidate)
    # Stable sorting applies the least significant tie-break first.
    for tie_break in reversed(RANKING_POLICY.candidate_tie_breaks):
        ranked.sort(
            key=lambda candidate: candidate_tie_break(candidate, tie_break.field),
            reverse=tie_break.descending,
        )
    ranked.sort(key=candidate_score, reverse=True)
    for rank, candidate in enumerate(ranked, start=1):
        assert candidate.ranking is not None
        candidate.ranking.rank = rank
    selected = ranked[: criteria.recommendation_limit]
    for candidate in selected:
        candidate.outcome = "recommended"
    return [candidate.stone_id for candidate in selected]
