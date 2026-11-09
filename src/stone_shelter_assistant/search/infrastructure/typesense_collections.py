"""Typesense schema for operational stone search documents."""

from typing import Final

from typesense import AsyncClient
from typesense.types.collection import CollectionCreateSchema

OPERATIONAL_COLLECTION: Final[str] = "stones"

OPERATIONAL_COLLECTION_SCHEMA: Final[CollectionCreateSchema] = {
    "name": OPERATIONAL_COLLECTION,
    "fields": [
        # Common SearchDocument fields
        {"name": "title", "type": "string"},
        {"name": "text", "type": "string"},
        {"name": "language", "type": "string"},
        {"name": "source_key", "type": "string"},
        {"name": "schema_version", "type": "int32"},
        {"name": "projection_version", "type": "int32"},
        {"name": "source_revision", "type": "string"},
        {"name": "content_hash", "type": "string"},
        # Fields shared by cards and events
        {"name": "document_kind", "type": "string", "facet": True},
        {"name": "stone_external_id", "type": "string", "facet": True},
        {"name": "case_external_id", "type": "string", "facet": True},
        {"name": "case_number", "type": "string", "facet": True},
        {"name": "stone_type", "type": "string", "facet": True},
        # Stone cards
        {"name": "stone_size", "type": "string", "facet": True, "optional": True},
        {"name": "adoption_status", "type": "string", "facet": True, "optional": True},
        {"name": "current_shelter_id", "type": "string", "facet": True, "optional": True},
        {"name": "socialization_traits", "type": "string[]", "facet": True, "optional": True},
        {"name": "care_level", "type": "string", "facet": True, "optional": True},
        # Case events
        {"name": "event_external_id", "type": "string", "facet": True, "optional": True},
        {"name": "event_type", "type": "string", "facet": True, "optional": True},
        {"name": "occurred_at", "type": "int64", "optional": True},
    ],
}


async def ensure_operational_collection(client: AsyncClient) -> None:
    """Create the operational collection if it does not exist."""
    existing_collections = await client.collections.retrieve()

    if any(collection["name"] == OPERATIONAL_COLLECTION for collection in existing_collections):
        return

    await client.collections.create(OPERATIONAL_COLLECTION_SCHEMA)
