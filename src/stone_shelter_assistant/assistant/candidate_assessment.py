"""Apply availability, evidence and compatibility rules to each candidate."""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

from stone_shelter_assistant.assistant.candidate_criteria import (
    CompatibilityTarget,
    HouseholdFact,
    SearchCriteria,
)
from stone_shelter_assistant.assistant.candidate_evidence import (
    AssessmentStatus,
    CandidateEvidence,
    ConditionCheck,
    Evidence,
    SourceText,
    check_pair_conditions,
    evidence_order,
    source_for_finding,
    validate_evidence,
)
from stone_shelter_assistant.assistant.ranking_policy import (
    RANKING_POLICY,
    Action,
    Criterion,
    Finding,
    PairResult,
)
from stone_shelter_assistant.search.document_models import CompatibilityPairSearchDocument
from stone_shelter_assistant.search.enums import CompatibilityVerdict
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

type Outcome = Literal[
    "recommended",
    "conditional_option",
    "excluded",
    "eligible_over_limit",
    "facts_only",
    "criteria_unavailable",
]


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


class Reason(BaseModel):
    criterion: Literal["availability", "character", "compatibility"]
    finding: Finding
    required: bool
    question_quote: str | None = None
    criterion_id: str | None = None
    source_id: str | None = None
    status: str | None = None
    pair_key: str | None = None
    verdict: CompatibilityVerdict | None = None
    household_quote: str | None = None
    conditions_status: Literal["confirmed", "unconfirmed", "unmarked"] | None = None
    condition_checks: list[ConditionCheck] = Field(default_factory=list)
    evidence: list[Evidence] = Field(default_factory=list)
    chosen_evidence: Evidence | None = None
    conflict: bool = False
    unknown_reason: (
        Literal["missing_evidence", "invalid_source_ref", "assessment_invalid"] | None
    ) = None
    policy_rule: str | None = None
    base_score: float | None = None
    action: Action = "rank"
    lookup_only: bool = False


class CandidateEvaluation(BaseModel):
    stone_id: str
    external_id: str
    eligible: bool
    reasons: list[Reason]
    exclusion_rules: list[str]
    outcome: Outcome = "facts_only"
    ranking: RankingCalculation | None = None


def character_reasons(
    stone_id: str,
    criteria: SearchCriteria,
    sources: Mapping[str, SourceText],
    assessment: CandidateEvidence,
    assessment_status: AssessmentStatus,
) -> list[Reason]:
    """Use the strongest applicable source and preserve competing quotes."""
    reasons = []
    for group, required in ((criteria.requirements, True), (criteria.preferences, False)):
        for criterion in group.character:
            findings = [
                item
                for item in assessment.character
                if item.stone_id == stone_id
                and item.criterion_id == criterion.criterion_id
                and item.fragment_id == criterion.fragment_id
            ]
            evidence = validate_evidence(
                findings,
                sources,
                "character",
            )
            # General knowledge can inform preferences, but cannot establish an individual requirement.
            chosen = next(
                (item for item in evidence if not required or item.supports_requirement),
                None,
            )
            unknown_reason: (
                Literal["missing_evidence", "invalid_source_ref", "assessment_invalid"] | None
            ) = None
            if chosen is None:
                unknown_reason = (
                    "assessment_invalid"
                    if assessment_status in {"invalid_response", "invalid_criterion_binding"}
                    else "invalid_source_ref"
                    if assessment_status == "invalid_source_ref"
                    or any(source_for_finding(item, sources) is None for item in findings)
                    else "missing_evidence"
                )
            reasons.append(
                Reason(
                    criterion="character",
                    finding=chosen.finding if chosen else "unknown",
                    required=required,
                    question_quote=criterion.question_quote,
                    criterion_id=criterion.criterion_id,
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
    assessment: CandidateEvidence,
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
    verdict = pair.verdict if pair is not None else None
    checks = (
        check_pair_conditions(pair, facts)
        if pair and verdict == CompatibilityVerdict.CONDITIONAL
        else []
    )
    conditions_status: Literal["confirmed", "unconfirmed", "unmarked"] | None = None
    result: PairResult = "unknown_existing_household" if target.existing_household else "unknown"
    match verdict:
        case CompatibilityVerdict.HARMONIOUS:
            result = "harmonious"
        case CompatibilityVerdict.CONDITIONAL:
            confirmed = bool(checks) and all(check.status == "confirmed" for check in checks)
            conditions_status = (
                "confirmed" if confirmed else "unconfirmed" if checks else "unmarked"
            )
            result = "conditions_confirmed" if confirmed else "conditions_unconfirmed"
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
    if (
        cohabitation is not None
        and pair_rule.action != "exclude"
        and not (result == "conditions_unconfirmed" and cohabitation.finding == "confirmed")
    ):
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
        conditions_status=conditions_status,
        condition_checks=checks,
        evidence=([pair_evidence] if pair_evidence else []) + individual,
        chosen_evidence=chosen,
        conflict=conflict,
        unknown_reason="missing_evidence" if rule.finding == "unknown" else None,
        policy_rule=result,
        base_score=rule.score,
        action="rank" if target.lookup_only else rule.action,
        lookup_only=target.lookup_only,
    )


def evaluate_candidate(
    criteria: SearchCriteria | None,
    card: StoneDetails,
    status: str | None,
    pairs: Mapping[str, CompatibilityPairSearchDocument | None],
    sources: Mapping[str, SourceText],
    assessment: CandidateEvidence,
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
