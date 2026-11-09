from typing import Final

from qdrant_client import AsyncQdrantClient, models

OPERATIONAL_COLLECTION: Final[str] = "stones"
KNOWLEDGE_COLLECTION: Final[str] = "knowledge"

KEYWORD_FILTER_FIELDS: Final[tuple[str, ...]] = (
    "document_kind",
    "stone_external_id",
    "case_external_id",
    "case_number",
    "stone_type",
    "stone_size",
    "adoption_status",
    "current_shelter_id",
    "socialization_traits",
    "care_level",
    "event_external_id",
    "event_type",
)

KNOWLEDGE_KEYWORD_FILTER_FIELDS: Final[tuple[str, ...]] = (
    "document_kind",
    "language",
    "stone_types",
    "pair_key",
    "verdict",
)


async def ensure_operational_collection(
    client: AsyncQdrantClient,
    vector_size: int,
) -> None:
    if await client.collection_exists(OPERATIONAL_COLLECTION):
        return

    await client.create_collection(
        collection_name=OPERATIONAL_COLLECTION,
        vectors_config=models.VectorParams(
            size=vector_size,
            distance=models.Distance.COSINE,
        ),
    )

    for field_name in KEYWORD_FILTER_FIELDS:
        await client.create_payload_index(
            collection_name=OPERATIONAL_COLLECTION,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )

    await client.create_payload_index(
        collection_name=OPERATIONAL_COLLECTION,
        field_name="occurred_at",
        field_schema=models.PayloadSchemaType.INTEGER,
    )


async def ensure_knowledge_collection(client: AsyncQdrantClient, vector_size: int) -> None:
    if await client.collection_exists(KNOWLEDGE_COLLECTION):
        return

    await client.create_collection(
        collection_name=KNOWLEDGE_COLLECTION,
        vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
    )
    for field_name in KNOWLEDGE_KEYWORD_FILTER_FIELDS:
        await client.create_payload_index(
            collection_name=KNOWLEDGE_COLLECTION,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
            wait=True,
        )
