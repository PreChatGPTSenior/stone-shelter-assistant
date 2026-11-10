"""Static evidence, admission, and ranking policy for the search pilot."""

from dataclasses import dataclass
from typing import Literal

from stone_shelter_assistant.stones.enums import AdoptionStatus

type Criterion = Literal["compatibility", "character"]
type Finding = Literal["confirmed", "conditional", "unknown", "contradicted"]
type SourceKind = Literal["profile", "biography", "encyclopedia", "compatibility_pair"]
type PairResult = Literal[
    "harmonious",
    "conditions_confirmed",
    "conditions_unconfirmed",
    "not_recommended",
    "unknown",
    "unknown_existing_household",
    "individual_conflict",
    "individual_match",
]
type Action = Literal["rank", "conditional_option", "exclude"]


@dataclass(frozen=True)
class SourceRule:
    priority: int
    weight: float
    supports_requirement: bool


@dataclass(frozen=True)
class CriterionRule:
    weight: float
    aggregation: Literal["minimum", "mean", "maximum"]


@dataclass(frozen=True)
class PairRule:
    finding: Finding
    score: float
    action: Action


@dataclass(frozen=True)
class CandidateTieBreak:
    field: Literal["compatibility", "character", "external_id"]
    descending: bool


@dataclass(frozen=True)
class RankingPolicy:
    version: str
    shortlist_limit: int
    default_recommendation_limit: int
    criteria: dict[Criterion, CriterionRule]
    sources: dict[Criterion, dict[SourceKind, SourceRule]]
    character_scores: dict[Finding, float]
    pair_rules: dict[PairResult, PairRule]
    target_priority: dict[Literal["requirement", "preference", "household_fact"], int]
    evidence_finding_priority: dict[Finding, int]
    evidence_tie_breaks: tuple[Literal["source_id", "field", "quote"], ...]
    candidate_tie_breaks: tuple[CandidateTieBreak, ...]
    eligible_status: AdoptionStatus
    required_findings: tuple[Finding, ...]
    cohabitation_resolution: Literal["pair_with_individual_veto", "source_priority"]
    missing_source_weight: float
    missing_tie_break_score: float
    score_precision: int


RANKING_POLICY = RankingPolicy(
    version="candidate-evaluation-v3",
    shortlist_limit=3,
    default_recommendation_limit=3,
    criteria={
        "compatibility": CriterionRule(weight=0.60, aggregation="minimum"),
        "character": CriterionRule(weight=0.40, aggregation="mean"),
    },
    sources={
        "character": {
            "profile": SourceRule(priority=1, weight=1.00, supports_requirement=True),
            "biography": SourceRule(priority=2, weight=0.85, supports_requirement=True),
            "encyclopedia": SourceRule(priority=3, weight=0.50, supports_requirement=False),
        },
        "compatibility": {
            "compatibility_pair": SourceRule(priority=1, weight=1.00, supports_requirement=True),
            "profile": SourceRule(priority=2, weight=1.00, supports_requirement=True),
            "biography": SourceRule(priority=3, weight=0.85, supports_requirement=True),
        },
    },
    character_scores={
        "confirmed": 1.00,
        "conditional": 0.50,
        "unknown": 0.25,
        "contradicted": 0.00,
    },
    pair_rules={
        "harmonious": PairRule("confirmed", 1.00, "rank"),
        "conditions_confirmed": PairRule("confirmed", 0.75, "rank"),
        "conditions_unconfirmed": PairRule("conditional", 0.50, "conditional_option"),
        "not_recommended": PairRule("contradicted", 0.00, "exclude"),
        "unknown": PairRule("unknown", 0.25, "rank"),
        "unknown_existing_household": PairRule("unknown", 0.25, "conditional_option"),
        "individual_conflict": PairRule("contradicted", 0.00, "exclude"),
        "individual_match": PairRule("confirmed", 1.00, "rank"),
    },
    target_priority={"requirement": 1, "preference": 2, "household_fact": 3},
    evidence_finding_priority={"contradicted": 1, "confirmed": 2, "conditional": 3, "unknown": 4},
    evidence_tie_breaks=("source_id", "field", "quote"),
    candidate_tie_breaks=(
        CandidateTieBreak("compatibility", descending=True),
        CandidateTieBreak("external_id", descending=False),
    ),
    eligible_status=AdoptionStatus.AVAILABLE,
    required_findings=("confirmed",),
    cohabitation_resolution="pair_with_individual_veto",
    missing_source_weight=1.00,
    missing_tie_break_score=0.00,
    score_precision=6,
)
