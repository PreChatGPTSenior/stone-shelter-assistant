"""Build search documents from stored stones and shelter cases."""

import json

from stone_shelter.search.document_content import build_embedding_text, calculate_text_hash
from stone_shelter.search.document_models import (
    DEFAULT_LANGUAGE,
    PROJECTION_VERSION,
    SEARCH_SCHEMA_VERSION,
    StoneSearchDocument,
)
from stone_shelter.stones.models import ShelterCaseModel, StoneModel


def build_stone_document(
    stone: StoneModel,
    case: ShelterCaseModel,
) -> StoneSearchDocument:
    """Build one stone search document with current case filters."""

    biography = (stone.biography or "").strip()
    text = biography or stone.name

    document_data: dict[str, str | int] = {
        "id": str(stone.id),
        "title": stone.name,
        "text": text,
        "language": DEFAULT_LANGUAGE,
        "source_key": f"stone:{stone.external_id}",
        "schema_version": SEARCH_SCHEMA_VERSION,
        "projection_version": PROJECTION_VERSION,
        "stone_external_id": str(stone.external_id),
        "case_external_id": str(case.external_id),
        "case_number": case.case_number,
        "stone_type": stone.stone_type,
        "stone_size": stone.stone_size,
        "adoption_status": case.adoption_status,
        "current_shelter_id": str(case.current_shelter_id),
    }

    source_data = {
        key: value
        for key, value in document_data.items()
        if key
        not in {
            "language",
            "source_key",
            "schema_version",
            "projection_version",
        }
    }

    document_data["source_revision"] = calculate_text_hash(
        json.dumps(
            source_data,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        )
    )

    document_data["content_hash"] = calculate_text_hash(build_embedding_text(stone.name, text))

    return StoneSearchDocument.model_validate(document_data)
