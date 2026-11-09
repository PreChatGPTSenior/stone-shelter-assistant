"""Build operational search documents from a stone, its profile, and its case."""

import json
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, uuid5

from stone_shelter_assistant.search.document_content import (
    build_embedding_text,
    calculate_text_hash,
)
from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    PROJECTION_VERSION,
    SEARCH_SCHEMA_VERSION,
    CaseEventSearchDocument,
    StoneSearchDocument,
)
from stone_shelter_assistant.stones.models import (
    CaseEventModel,
    ShelterCaseModel,
    StoneModel,
    StoneProfileModel,
)

_UNIX_EPOCH = datetime(1970, 1, 1, tzinfo=UTC)


def build_stone_document(
    stone: StoneModel,
    case: ShelterCaseModel,
    profile: StoneProfileModel | None = None,
) -> StoneSearchDocument:
    """Build one stone card with its supplied profile and current case filters."""
    traits = sorted(profile.socialization_traits) if profile is not None else []
    care_level = profile.care_level if profile is not None else None
    text_blocks = []
    if biography := (stone.biography or "").strip():
        text_blocks.append(biography)
    if traits:
        labels = ", ".join(trait.replace("_", " ").lower() for trait in traits)
        text_blocks.append(f"Socialization: {labels}")
    if care_level is not None:
        text_blocks.append(f"Care level: {care_level.lower()}")
    if profile is not None:
        for label, value in (
            ("Health notes", profile.health_notes),
            ("Trigger notes", profile.trigger_notes),
            ("Preferred environment", profile.preferred_environment),
        ):
            if value and value.strip():
                text_blocks.append(f"{label}: {value.strip()}")

    text = "\n\n".join(text_blocks) or stone.name
    return StoneSearchDocument.model_validate(
        _document_fields(
            source_key=f"stone:{stone.external_id}",
            title=stone.name,
            text=text,
            source_data={
                "id": str(stone.id),
                **_stone_and_case_fields(stone, case),
                "stone_size": stone.stone_size,
                "adoption_status": case.adoption_status,
                "current_shelter_id": str(case.current_shelter_id),
                "socialization_traits": traits,
                "care_level": care_level,
            },
        )
    )


def build_case_event_document(
    stone: StoneModel,
    case: ShelterCaseModel,
    event: CaseEventModel,
) -> CaseEventSearchDocument:
    """Build one historical document with a stable ID derived from the source event."""
    source_key = f"case-event:{event.external_id}"
    event_label = event.event_type.replace("_", " ").capitalize()
    occurred_at = (event.occurred_at - _UNIX_EPOCH) // timedelta(microseconds=1)
    return CaseEventSearchDocument.model_validate(
        _document_fields(
            source_key=source_key,
            title=f"{stone.name} — {event_label}",
            text=event.event_notes,
            source_data={
                "id": str(
                    uuid5(
                        NAMESPACE_URL, f"urn:stone-shelter-assistant:search-document:{source_key}"
                    )
                ),
                **_stone_and_case_fields(stone, case),
                "event_external_id": str(event.external_id),
                "event_type": event.event_type,
                "occurred_at": occurred_at,
            },
        )
    )


def _stone_and_case_fields(stone: StoneModel, case: ShelterCaseModel) -> dict[str, str]:
    return {
        "stone_external_id": str(stone.external_id),
        "case_external_id": str(case.external_id),
        "case_number": case.case_number,
        "stone_type": stone.stone_type,
    }


def _document_fields(
    *,
    source_key: str,
    title: str,
    text: str,
    source_data: dict[str, str | int | list[str] | None],
) -> dict[str, object]:
    source_data = {**source_data, "title": title, "text": text}
    source_json = json.dumps(source_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return {
        **source_data,
        "language": DEFAULT_LANGUAGE,
        "source_key": source_key,
        "schema_version": SEARCH_SCHEMA_VERSION,
        "projection_version": PROJECTION_VERSION,
        "source_revision": calculate_text_hash(source_json),
        "content_hash": calculate_text_hash(build_embedding_text(title, text)),
    }
