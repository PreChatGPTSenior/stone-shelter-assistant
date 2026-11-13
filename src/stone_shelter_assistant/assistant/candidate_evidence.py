"""Source-bound evidence models and validation for candidate assessment."""

import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Literal, Self
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError

from stone_shelter_assistant.assistant.candidate_criteria import HouseholdFact
from stone_shelter_assistant.assistant.ranking_policy import (
    RANKING_POLICY,
    Criterion,
    Finding,
    SourceKind,
)
from stone_shelter_assistant.assistant.reference_evidence import (
    case_event_source_data,
    case_event_source_id,
)
from stone_shelter_assistant.search.document_models import (
    CompatibilityPairSearchDocument,
    EncyclopediaSectionSearchDocument,
)
from stone_shelter_assistant.search.enums import AccommodationFactType
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.stone_contracts import StoneDetails

type AssessmentStatus = Literal[
    "not_needed", "parsed", "invalid_response", "invalid_source_ref", "invalid_criterion_binding"
]


type SourceRef = Literal[
    "biography",
    "profile.preferred_environment",
    "profile.trigger_notes",
    "profile.socialization_traits",
    "observation",
    "encyclopedia",
]


class QuotedFinding(BaseModel):
    model_config = ConfigDict(extra="forbid")

    stone_id: str
    source_ref: SourceRef
    finding: Literal["confirmed", "contradicted"]
    quote: str = Field(min_length=1)
    observation_external_id: UUID | None = None

    @model_validator(mode="after")
    def require_observation_id(self) -> Self:
        if self.source_ref == "observation" and self.observation_external_id is None:
            raise PydanticCustomError(
                "observation_source_id_required",
                "Observation evidence requires its event external ID",
            )
        return self


class CharacterFinding(QuotedFinding):
    criterion_id: str = Field(min_length=1)
    fragment_id: int


class IndividualCompatibilityFinding(QuotedFinding):
    pair_key: str
    scope: Literal["preference", "cohabitation"]


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    character: list[CharacterFinding]
    individual_compatibility: list[IndividualCompatibilityFinding]


def assessment_failure_status(error: BaseException | None) -> AssessmentStatus:
    """Classify structured-output errors without interpreting source text as JSON."""
    while error is not None:
        if isinstance(error, ValidationError) and any(
            (item["type"] == "literal_error" and item["loc"][-1:] == ("source_ref",))
            or (
                item["type"] in {"value_error", "uuid_parsing"}
                and item["loc"][-1:] in {("source_ref",), ("observation_external_id",)}
            )
            or item["type"] == "observation_source_id_required"
            for item in error.errors()
        ):
            return "invalid_source_ref"
        error = error.__cause__ or error.__context__
    return "invalid_response"


@dataclass(frozen=True)
class SourceText:
    kind: Literal["profile", "observation", "biography", "encyclopedia"]
    source_id: str
    field: str
    text: str
    event_external_id: str | None = None
    event_type: str | None = None
    occurred_at: str | None = None
    stone_id: str | None = None
    case_external_id: str | None = None


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


class ConditionCheck(BaseModel):
    condition_id: str
    fact_type: AccommodationFactType
    expected_value: bool
    rule_quote: str
    status: Literal["confirmed", "contradicted", "unknown", "conflict", "invalid_rule"]
    facts: list[HouseholdFact] = Field(default_factory=list)


def check_pair_conditions(
    pair: CompatibilityPairSearchDocument, facts: list[HouseholdFact]
) -> list[ConditionCheck]:
    """Compare every authored condition with typed household facts, without model verdicts."""
    checks = []
    condition_ids = [condition.id for condition in pair.conditions]
    for condition in pair.conditions:
        matching = [
            fact
            for fact in facts
            if fact.fact_type == condition.fact_type
            and (
                fact.applies_to_pair is None
                or build_pair_key(*fact.applies_to_pair) == pair.pair_key
            )
        ]
        values = {fact.value for fact in matching}
        status: Literal["confirmed", "contradicted", "unknown", "conflict", "invalid_rule"]
        if condition.source_quote not in pair.text or condition_ids.count(condition.id) != 1:
            status = "invalid_rule"
        elif not matching:
            status = "unknown"
        elif len(values) != 1:
            status = "conflict"
        elif condition.expected_value in values:
            status = "confirmed"
        else:
            status = "contradicted"
        checks.append(
            ConditionCheck(
                condition_id=condition.id,
                fact_type=condition.fact_type,
                expected_value=condition.expected_value,
                rule_quote=condition.source_quote,
                status=status,
                facts=matching,
            )
        )
    return checks


def candidate_sources(
    card: StoneDetails,
    encyclopedia: EncyclopediaSectionSearchDocument | None,
    observations: Sequence[Mapping[str, str]] = (),
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
    for event in observations:
        event_id = event["event_external_id"]
        data = case_event_source_data(
            event,
            stone_id=str(card.id),
            case_external_id=str(card.shelter_case.external_id),
        )
        sources[f"observation:{event_id}"] = SourceText(
            "observation",
            case_event_source_id(event_id),
            "event_notes",
            data["event_notes"],
            event_external_id=data["event_external_id"],
            event_type=data["event_type"],
            occurred_at=data["occurred_at"],
            stone_id=data["stone_id"],
            case_external_id=data["case_external_id"],
        )
    return sources


CHARACTER_CONTEXT_SECTIONS = {"### Psychological Vibe", "### Ideal Places at Home"}


def assessment_source_text(source: SourceText) -> str:
    """Select authored character sections without summarizing or prioritizing evidence."""
    if source.kind != "encyclopedia":
        return source.text
    sections = re.split(r"(?m)(?=^### )", source.text)
    fragments = [
        line.strip()
        for line in sections[0].splitlines()
        if line.startswith("**Character archetype:**")
    ]
    fragments.extend(
        section.strip()
        for section in sections[1:]
        if section.splitlines()[0].strip() in CHARACTER_CONTEXT_SECTIONS
    )
    # Preserve evidence from documents whose section structure is not recognized.
    return "\n\n".join(fragments) if fragments else source.text


def validate_evidence(
    findings: Sequence[QuotedFinding],
    sources: Mapping[str, SourceText],
    criterion: Criterion,
) -> list[Evidence]:
    """Keep exact quotes from the referenced field and rank them by source."""
    evidence = []
    for finding in findings:
        source = source_for_finding(finding, sources)
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


def source_for_finding(
    finding: QuotedFinding, sources: Mapping[str, SourceText]
) -> SourceText | None:
    if finding.source_ref == "observation":
        return sources.get(f"observation:{finding.observation_external_id}")
    return sources.get(finding.source_ref)


def evidence_order(item: Evidence) -> tuple[int, int, tuple[str, ...]]:
    return (
        item.priority,
        RANKING_POLICY.evidence_finding_priority[item.finding],
        tuple(str(getattr(item, field) or "") for field in RANKING_POLICY.evidence_tie_breaks),
    )
