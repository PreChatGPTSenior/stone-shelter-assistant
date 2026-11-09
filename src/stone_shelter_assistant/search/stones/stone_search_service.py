"""Retrieve stone cards through lexical or vector search."""

from typing import Final

from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.document_models import StoneSearchDocument
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.stones.search_contracts import StoneSearchFilters

LEXICAL_FIELDS: Final[str] = (
    "title,text,case_number,stone_external_id,case_external_id,stone_type,stone_size,"
    "adoption_status,current_shelter_id,care_level,socialization_traits,language"
)


class StoneSearchService:
    def __init__(
        self, typesense: AsyncClient, qdrant: AsyncQdrantClient, embeddings: Embeddings
    ) -> None:
        self._typesense = typesense
        self._qdrant = qdrant
        self._embeddings = embeddings

    async def search_lexical(
        self, query: str = "", filters: StoneSearchFilters | None = None, limit: int = 5
    ) -> list[StoneSearchDocument]:
        documents = self._typesense.collections[
            typesense_collections.OPERATIONAL_COLLECTION
        ].documents
        result = await documents.search(
            {
                "q": query.strip() or "*",
                "query_by": LEXICAL_FIELDS,
                "filter_by": " && ".join(
                    f"{field}:=`{value}`" for field, value in _exact_matches(filters)
                ),
                "per_page": limit,
            }
        )
        return [
            StoneSearchDocument.model_validate(hit["document"]) for hit in result.get("hits", [])
        ]

    async def search_semantic(
        self, query: str, filters: StoneSearchFilters | None = None, limit: int = 5
    ) -> list[StoneSearchDocument]:
        query = query.strip()
        if not query:
            raise ValueError("Semantic search requires a query")
        result = await self._qdrant.query_points(
            collection_name=qdrant_collections.OPERATIONAL_COLLECTION,
            query=await self._embeddings.aembed_query(query),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key=field, match=models.MatchValue(value=value))
                    for field, value in _exact_matches(filters)
                ]
            ),
            limit=limit,
            with_payload=True,
        )
        return [
            StoneSearchDocument.model_validate({**(point.payload or {}), "id": point.id})
            for point in result.points
        ]


def _exact_matches(filters: StoneSearchFilters | None) -> list[tuple[str, str]]:
    matches = [("document_kind", DocumentKind.STONE.value)]
    if filters is not None:
        matches.extend(
            filters.model_dump(
                mode="json", exclude_none=True, exclude={"socialization_traits"}
            ).items()
        )
        matches.extend(
            ("socialization_traits", trait.value) for trait in filters.socialization_traits
        )
    return matches
