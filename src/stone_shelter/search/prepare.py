"""Build search documents from stored stones and shelter cases."""

import json
from hashlib import sha256

from stone_shelter.adoption.persistence.models import ShelterCaseModel
from stone_shelter.catalog.persistence.models import StoneModel
from stone_shelter.search.documents import (
    LANGUAGE_VERSION,
    PROJECTION_VERSION,
    SEARCH_SCHEMA_VERSION,
    StoneSearchDocument,
)


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
        "language": LANGUAGE_VERSION,
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
        if key not in {
            "language",
            "source_key",
            "schema_version",
            "projection_version",
        }
    }

    document_data["source_revision"] = content_hash(json.dumps(
        source_data,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ))

    document_data["content_hash"] = content_hash(f"{document_data['title']}\n\n{document_data['text']}")


    return StoneSearchDocument.model_validate(document_data)

def content_hash(input):
    return f"sha256:{sha256(input.encode('utf-8')).hexdigest()}"


def embedding_text(document: StoneSearchDocument) -> str:
    """Return the exact text sent to the embedding model."""

    return f"{document.title}\n\n{document.text}"