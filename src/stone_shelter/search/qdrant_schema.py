from typing import Final

from qdrant_client import AsyncQdrantClient, models

OPERATIONAL_COLLECTION: Final[str] = "operational_stone_search_documents"

FILTER_FIELDS: Final[tuple[str, ...]] = (
    "document_kind",
    "stone_type",
    "stone_size",
    "adoption_status",
    "current_shelter_id",
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

    for field_name in FILTER_FIELDS:
        await client.create_payload_index(
            collection_name=OPERATIONAL_COLLECTION,
            field_name=field_name,
            field_schema=models.PayloadSchemaType.KEYWORD,
        )