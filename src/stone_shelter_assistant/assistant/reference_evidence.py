"""Keep individual facts separate from type knowledge in reference answers."""

from collections.abc import Mapping
from typing import Literal

from pydantic import BaseModel, Field

type ReferenceScope = Literal["individual", "history", "encyclopedia", "compatibility"]


class ReferenceSource(BaseModel):
    source_id: str
    scope: ReferenceScope
    text: str
    event_type: str | None = None
    occurred_at: str | None = None
    stone_id: str | None = None
    case_external_id: str | None = None


def case_event_source_id(event_external_id: str) -> str:
    return f"case-event:{event_external_id}"


def case_event_source_data(
    event: Mapping[str, str], *, stone_id: str, case_external_id: str
) -> dict[str, str]:
    """Attach each immutable event to the card and shelter case it came from."""
    return {
        "stone_id": stone_id,
        "case_external_id": case_external_id,
        "event_external_id": event["event_external_id"],
        "event_type": event["event_type"],
        "occurred_at": event["occurred_at"],
        "event_notes": event["event_notes"],
    }


class ReferenceQuote(BaseModel):
    source_id: str
    quote: str = Field(min_length=1)


class ReferenceEvidence(BaseModel):
    quotes: list[ReferenceQuote]


class GroundedReferenceQuote(ReferenceQuote):
    scope: ReferenceScope
    event_type: str | None = None
    occurred_at: str | None = None
    stone_id: str | None = None
    case_external_id: str | None = None


class ReferenceSection(BaseModel):
    scope: ReferenceScope
    explanation: str = Field(min_length=1)
    source_ids: list[str] = Field(min_length=1)


class ReferenceAnswer(BaseModel):
    sections: list[ReferenceSection] = Field(min_length=1, max_length=4)


def check_reference_quotes(
    evidence: ReferenceEvidence, sources: Mapping[str, ReferenceSource]
) -> tuple[list[GroundedReferenceQuote], list[dict[str, str]]]:
    """Validate exact source/quote binding; scope is assigned by code, not the model."""
    accepted = []
    rejected = []
    for item in evidence.quotes:
        source = sources.get(item.source_id)
        reason = (
            "unknown_source_ref"
            if source is None
            else "non_verbatim_quote"
            if not item.quote.strip() or item.quote not in source.text
            else None
        )
        if reason is not None:
            rejected.append({**item.model_dump(), "reason": reason})
        elif source is not None:
            accepted.append(
                GroundedReferenceQuote(
                    **item.model_dump(),
                    scope=source.scope,
                    event_type=source.event_type,
                    occurred_at=source.occurred_at,
                    stone_id=source.stone_id,
                    case_external_id=source.case_external_id,
                )
            )
    return accepted, rejected


def reference_citations_valid(
    answer: ReferenceAnswer, quotes: list[GroundedReferenceQuote]
) -> bool:
    """Check citation identity/scope coverage, not explanation entailment or completeness."""
    scopes = {quote.source_id: quote.scope for quote in quotes}
    return {section.scope for section in answer.sections} == set(scopes.values()) and all(
        scopes.get(source_id) == section.scope
        for section in answer.sections
        for source_id in section.source_ids
    )


SCOPE_TITLES: dict[ReferenceScope, str] = {
    "individual": "Individual facts",
    "history": "Case history",
    "encyclopedia": "General type information",
    "compatibility": "General type compatibility",
}
