"""Typesense schemas for operational stones and reference knowledge."""

from typing import Final

from typesense import AsyncClient
from typesense.types.collection import (
    CollectionCreateSchema,
    ReferenceCollectionFieldSchema,
    RegularCollectionFieldSchema,
)

OPERATIONAL_COLLECTION: Final[str] = "stones"

KNOWLEDGE_COLLECTION: Final[str] = "knowledge"
GROUNDING_COLLECTION: Final[str] = "grounding_catalog"

GROUNDING_COLLECTION_SCHEMA: Final[CollectionCreateSchema] = {
    "name": GROUNDING_COLLECTION,
    "fields": [
        {"name": "language", "type": "string", "facet": True},
        {"name": "catalog_version", "type": "string", "facet": True},
        {"name": "concept_id", "type": "string", "facet": True},
        {"name": "entry_kind", "type": "string", "facet": True},
        {"name": "text", "type": "string"},
        {"name": "expected", "type": "string", "optional": True},
        {"name": "proposed_value", "type": "bool", "optional": True},
        {"name": "proposed_type", "type": "string", "optional": True},
    ],
}


async def ensure_grounding_collection(client: AsyncClient) -> None:
    await _ensure_collection(client, GROUNDING_COLLECTION_SCHEMA)


COMMON_DOCUMENT_FIELDS: Final[
    list[RegularCollectionFieldSchema | ReferenceCollectionFieldSchema]
] = [
    {"name": "title", "type": "string"},
    {"name": "text", "type": "string"},
    {"name": "source_key", "type": "string"},
    {"name": "schema_version", "type": "int32"},
    {"name": "projection_version", "type": "int32"},
    {"name": "source_revision", "type": "string"},
    {"name": "content_hash", "type": "string"},
    {"name": "document_kind", "type": "string", "facet": True},
]

OPERATIONAL_COLLECTION_SCHEMA: Final[CollectionCreateSchema] = {
    "name": OPERATIONAL_COLLECTION,
    "fields": [
        *COMMON_DOCUMENT_FIELDS,
        {"name": "language", "type": "string"},
        # Fields shared by cards and events
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


KNOWLEDGE_COLLECTION_SCHEMA: Final[CollectionCreateSchema] = {
    "name": KNOWLEDGE_COLLECTION,
    "fields": [
        *COMMON_DOCUMENT_FIELDS,
        {"name": "language", "type": "string", "facet": True},
        {"name": "source_path", "type": "string"},
        {"name": "section_path", "type": "string[]", "optional": True},
        {"name": "stone_types", "type": "string[]", "facet": True, "optional": True},
        {"name": "pair_key", "type": "string", "facet": True, "optional": True},
        {"name": "verdict", "type": "string", "facet": True, "optional": True},
    ],
}


async def ensure_operational_collection(client: AsyncClient) -> None:
    await _ensure_collection(client, OPERATIONAL_COLLECTION_SCHEMA)


async def ensure_knowledge_collection(client: AsyncClient) -> None:
    await _ensure_collection(client, KNOWLEDGE_COLLECTION_SCHEMA)


async def _ensure_collection(client: AsyncClient, schema: CollectionCreateSchema) -> None:
    existing_collections = await client.collections.retrieve()
    if not any(collection["name"] == schema["name"] for collection in existing_collections):
        await client.collections.create(schema)
