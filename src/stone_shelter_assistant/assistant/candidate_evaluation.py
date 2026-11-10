"""Apply the pilot's recommendation rules to checked candidate evidence."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, Field

from stone_shelter_assistant.assistant.ranking_policy import (
    RANKING_POLICY,
    Action,
    Criterion,
    Finding,
    PairResult,
    SourceKind,
)
from stone_shelter_assistant.search.document_models import (
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.search.enums import CompatibilityVerdict
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.enums import StoneType
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

type Outcome = Literal[
    "recommended",
    "conditional_option",
    "excluded",
    "eligible_over_limit",
    "facts_only",
    "criteria_unavailable",
]
type AssessmentStatus = Literal["not_needed", "parsed", "invalid_response"]


class QuotedCriterion(BaseModel):
    question_quote: str = Field(min_length=1)


class HouseholdFact(QuotedCriterion):
    existing_stone_type: StoneType | None = None


class CompatibilityCriterion(QuotedCriterion):
    household_type: StoneType


class CriteriaGroup(BaseModel):
    character: list[QuotedCriterion]
    compatibility: list[CompatibilityCriterion]


@dataclass(frozen=True)
class CompatibilityTarget:
    quote: str
    required: bool
    existing_household: bool


class SearchCriteria(BaseModel):
    recommendation_limit: int = Field(ge=0, le=RANKING_POLICY.shortlist_limit)
    household_facts: list[HouseholdFact]
    requirements: CriteriaGroup
    preferences: CriteriaGroup

    def quotes(self) -> list[str]:
        """Return the verbatim excerpts used to extract the request."""
        return [
            item.question_quote
            for item in (
                *self.household_facts,
                *self.requirements.character,
                *self.requirements.compatibility,
                *self.preferences.character,
                *self.preferences.compatibility,
            )
        ]

    def compatibility_targets(self) -> dict[StoneType, CompatibilityTarget]:
        """Check explicit pair criteria and types already living in the household."""
        facts = {
            fact.existing_stone_type: fact.question_quote
            for fact in self.household_facts
            if fact.existing_stone_type is not None
        }
        groups = {
            "household_fact": list(facts.items()),
            "preference": [
                (item.household_type, item.question_quote)
                for item in self.preferences.compatibility
            ],
            "requirement": [
                (item.household_type, item.question_quote)
                for item in self.requirements.compatibility
            ],
        }
        required_types = {item.household_type for item in self.requirements.compatibility}
        targets: dict[StoneType, CompatibilityTarget] = {}
        for group in sorted(
            RANKING_POLICY.target_priority, key=RANKING_POLICY.target_priority.__getitem__
        ):
            for stone_type, quote in groups[group]:
                targets.setdefault(
                    stone_type,
                    CompatibilityTarget(quote, stone_type in required_types, stone_type in facts),
                )
        return targets


class QuotedFinding(BaseModel):
    stone_id: str
    source_ref: str
    finding: Literal["confirmed", "contradicted"]
    quote: str = Field(min_length=1)


class CharacterFinding(QuotedFinding):
    question_quote: str


class IndividualCompatibilityFinding(QuotedFinding):
    pair_key: str
    scope: Literal["preference", "cohabitation"]


class ConfirmedAccommodation(BaseModel):
    pair_key: str
    household_quote: str = Field(min_length=1)
    pair_quote: str = Field(min_length=1)


class AssessedEvidence(BaseModel):
    character: list[CharacterFinding] = Field(default_factory=list)
    individual_compatibility: list[IndividualCompatibilityFinding] = Field(default_factory=list)
    accommodations: list[ConfirmedAccommodation] = Field(default_factory=list)


@dataclass(frozen=True)
class SourceText:
    kind: Literal["profile", "biography", "encyclopedia"]
    source_id: str
    field: str
    text: str


class Evidence(BaseModel):
    source_id: str
    field: str
    source_kind: SourceKind
    priority: int
    weight: float
    supports_requirement: bool
    finding: Finding
    quote: str | None = None
    scope: Literal["preference", "cohabitation"] | None = None


class Reason(BaseModel):
    criterion: Literal["availability", "character", "compatibility"]
    finding: Finding
    required: bool
    question_quote: str | None = None
    source_id: str | None = None
    status: str | None = None
    pair_key: str | None = None
    verdict: CompatibilityVerdict | None = None
    household_quote: str | None = None
    evidence: list[Evidence] = Field(default_factory=list)
    chosen_evidence: Evidence | None = None
    conflict: bool = False
    unknown_reason: Literal["missing_evidence", "assessment_invalid"] | None = None
    policy_rule: str | None = None
    base_score: float | None = None
    action: Action = "rank"


class ScoredReason(BaseModel):
    rule: str | None
    question_quote: str | None
    source_id: str | None
    base_score: float
    source_weight: float
    adjusted_score: float


class CriterionScore(BaseModel):
    aggregation: str
    weight: float
    effective_weight: float
    score: float
    contribution: float
    reasons: list[ScoredReason]


class RankingCalculation(BaseModel):
    criteria: dict[Criterion, CriterionScore]
    total: float | None
    tie_break_values: dict[str, float | str] = Field(default_factory=dict)
    rank: int | None = None


class CandidateEvaluation(BaseModel):
    stone_id: str
    external_id: str
    eligible: bool
    reasons: list[Reason]
    exclusion_rules: list[str]
    outcome: Outcome = "facts_only"
    ranking: RankingCalculation | None = None


def candidate_sources(
    card: StoneDetails, encyclopedia: EncyclopediaSectionSearchDocument | None
) -> dict[str, SourceText]:
    """Label each source before the model sees the text."""
    card_id = f"stone-card:{card.id}"
    sources = {"biography": SourceText("biography", card_id, "biography", card.biography or "")}
    if card.profile is not None:
        fields = {
            "preferred_environment": card.profile.preferred_environment or "",
            "trigger_notes": card.profile.trigger_notes or "",
            "socialization_traits": ", ".join(card.profile.socialization_traits),
        }
        sources.update(
            (f"profile.{field}", SourceText("profile", card_id, field, value))
            for field, value in fields.items()
        )
    if encyclopedia is not None:
        sources["encyclopedia"] = SourceText(
            "encyclopedia", encyclopedia.source_key, "text", encyclopedia.text
        )
    return sources


def validate_evidence(
    findings: Sequence[QuotedFinding], sources: Mapping[str, SourceText], criterion: Criterion
) -> list[Evidence]:
    """Keep exact quotes from the referenced field and rank them by source."""
    evidence = []
    for finding in findings:
        source = sources.get(finding.source_ref)
        if source is not None and finding.quote.strip() and finding.quote in source.text:
            rule = RANKING_POLICY.sources[criterion].get(source.kind)
            if rule is None:
                continue
            evidence.append(
                Evidence(
                    source_id=source.source_id,
                    field=source.field,
                    source_kind=source.kind,
                    priority=rule.priority,
                    weight=rule.weight,
                    supports_requirement=rule.supports_requirement,
                    finding=finding.finding,
                    quote=finding.quote,
                    scope=(
                        finding.scope
                        if isinstance(finding, IndividualCompatibilityFinding)
                        else None
                    ),
                )
            )
    return sorted(evidence, key=evidence_order)


def evidence_order(item: Evidence) -> tuple[int, int, tuple[str, ...]]:
    return (
        item.priority,
        RANKING_POLICY.evidence_finding_priority[item.finding],
        tuple(str(getattr(item, field) or "") for field in RANKING_POLICY.evidence_tie_breaks),
    )


def character_reasons(
    stone_id: str,
    criteria: SearchCriteria,
    sources: Mapping[str, SourceText],
    assessment: AssessedEvidence,
    assessment_status: AssessmentStatus,
) -> list[Reason]:
    """Use the strongest applicable source and preserve competing quotes."""
    reasons = []
    for group, required in ((criteria.requirements, True), (criteria.preferences, False)):
        for criterion in group.character:
            evidence = validate_evidence(
                [
                    item
                    for item in assessment.character
                    if item.stone_id == stone_id and item.question_quote == criterion.question_quote
                ],
                sources,
                "character",
            )
            # General knowledge can inform preferences, but cannot establish an individual requirement.
            chosen = next(
                (item for item in evidence if not required or item.supports_requirement),
                None,
            )
            unknown_reason: Literal["missing_evidence", "assessment_invalid"] | None = None
            if chosen is None:
                unknown_reason = (
                    "assessment_invalid"
                    if assessment_status == "invalid_response"
                    else "missing_evidence"
                )
            reasons.append(
                Reason(
                    criterion="character",
                    finding=chosen.finding if chosen else "unknown",
                    required=required,
                    question_quote=criterion.question_quote,
                    evidence=evidence,
                    chosen_evidence=chosen,
                    conflict=len({item.finding for item in evidence}) > 1,
                    unknown_reason=unknown_reason,
                    policy_rule=chosen.finding if chosen else "unknown",
                    base_score=RANKING_POLICY.character_scores[
                        chosen.finding if chosen else "unknown"
                    ],
                )
            )
    return reasons


def compatibility_reason(
    stone_id: str,
    key: str,
    target: CompatibilityTarget,
    pair: CompatibilityPairSearchDocument | None,
    facts: list[HouseholdFact],
    sources: Mapping[str, SourceText],
    assessment: AssessedEvidence,
) -> Reason:
    """Keep the exact pair verdict and relevant individual observations separately."""
    individual = validate_evidence(
        [
            item
            for item in assessment.individual_compatibility
            if item.stone_id == stone_id and item.pair_key == key
        ],
        sources,
        "compatibility",
    )
    accommodation = next(
        (
            item
            for item in assessment.accommodations
            if item.pair_key == key
            and pair is not None
            and item.pair_quote.strip()
            and item.pair_quote in pair.text
            and item.household_quote.strip()
            and any(item.household_quote in fact.question_quote for fact in facts)
        ),
        None,
    )
    verdict = pair.verdict if pair is not None else None
    result: PairResult = "unknown_existing_household" if target.existing_household else "unknown"
    match verdict:
        case CompatibilityVerdict.HARMONIOUS:
            result = "harmonious"
        case CompatibilityVerdict.CONDITIONAL:
            result = "conditions_confirmed" if accommodation else "conditions_unconfirmed"
        case CompatibilityVerdict.NOT_RECOMMENDED:
            result = "not_recommended"
    pair_rule = RANKING_POLICY.pair_rules[result]
    source_rule = RANKING_POLICY.sources["compatibility"]["compatibility_pair"]
    pair_evidence = (
        Evidence(
            source_id=pair.source_key,
            source_kind="compatibility_pair",
            field="verdict",
            finding=pair_rule.finding,
            priority=source_rule.priority,
            weight=source_rule.weight,
            supports_requirement=source_rule.supports_requirement,
            quote=accommodation.pair_quote if accommodation else None,
        )
        if pair is not None
        else None
    )
    cohabitation = next(
        (
            item
            for item in individual
            if item.scope == "cohabitation" and (not target.required or item.supports_requirement)
        ),
        None,
    )
    cohabitation_findings = {item.finding for item in individual if item.scope == "cohabitation"}
    cohabitation_findings.add(pair_rule.finding)
    preference_findings = {item.finding for item in individual if item.scope == "preference"}
    conflict = {"confirmed", "contradicted"} <= cohabitation_findings or len(
        preference_findings
    ) > 1
    chosen = pair_evidence
    if cohabitation is not None and pair_rule.action != "exclude":
        if RANKING_POLICY.cohabitation_resolution == "source_priority":
            if pair_evidence is None or evidence_order(cohabitation) < evidence_order(
                pair_evidence
            ):
                chosen = cohabitation
        elif cohabitation.finding == "contradicted":
            chosen = cohabitation
    if chosen is not None and chosen is cohabitation:
        result = "individual_conflict" if chosen.finding == "contradicted" else "individual_match"
    rule = RANKING_POLICY.pair_rules[result]
    return Reason(
        criterion="compatibility",
        finding=rule.finding,
        required=target.required,
        question_quote=target.quote,
        source_id=pair.source_key if pair is not None else None,
        pair_key=key,
        verdict=verdict,
        household_quote=accommodation.household_quote if accommodation else None,
        evidence=([pair_evidence] if pair_evidence else []) + individual,
        chosen_evidence=chosen,
        conflict=conflict,
        unknown_reason="missing_evidence" if rule.finding == "unknown" else None,
        policy_rule=result,
        base_score=rule.score,
        action=rule.action,
    )


def evaluate_candidate(
    criteria: SearchCriteria | None,
    card: StoneDetails,
    status: str | None,
    pairs: Mapping[str, CompatibilityPairSearchDocument | None],
    sources: Mapping[str, SourceText],
    assessment: AssessedEvidence,
    assessment_status: AssessmentStatus,
) -> CandidateEvaluation:
    """Apply availability, compatibility vetoes, and explicit requirements."""
    stone_id = str(card.id)
    availability: Finding = "unknown"
    if status is not None:
        availability = "confirmed" if status == RANKING_POLICY.eligible_status else "contradicted"
    reasons = [
        Reason(
            criterion="availability",
            finding=availability,
            required=True,
            source_id="verified_statuses",
            status=status,
            unknown_reason="missing_evidence" if status is None else None,
        )
    ]
    exclusions = ["availability_not_confirmed"] if availability != "confirmed" else []
    if criteria is not None:
        reasons.extend(
            character_reasons(stone_id, criteria, sources, assessment, assessment_status)
        )
        for stone_type, target in criteria.compatibility_targets().items():
            key = build_pair_key(card.stone_type, stone_type)
            reasons.append(
                compatibility_reason(
                    stone_id,
                    key,
                    target,
                    pairs.get(key),
                    criteria.household_facts,
                    sources,
                    assessment,
                )
            )
        exclusions.extend(
            dict.fromkeys(
                reason.policy_rule
                for reason in reasons
                if reason.action == "exclude" and reason.policy_rule is not None
            )
        )
        if any(
            reason.criterion != "availability"
            and reason.required
            and (
                reason.finding not in RANKING_POLICY.required_findings
                or (
                    reason.chosen_evidence is not None
                    and not reason.chosen_evidence.supports_requirement
                )
            )
            for reason in reasons
        ):
            exclusions.append("requirement_not_met")
    return CandidateEvaluation(
        stone_id=stone_id,
        external_id=str(card.external_id),
        eligible=not exclusions,
        reasons=reasons,
        exclusion_rules=exclusions,
    )


def calculate_ranking(candidate: CandidateEvaluation) -> RankingCalculation:
    """Keep the score, source multiplier, and normalized contribution for each criterion."""
    groups: dict[Criterion, list[ScoredReason]] = {}
    for criterion in RANKING_POLICY.criteria:
        for reason in candidate.reasons:
            if reason.criterion != criterion or reason.base_score is None:
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
        candidate.ranking = calculate_ranking(candidate)
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
