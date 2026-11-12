"""Retrieve stone cards through lexical or vector search."""

from asyncio import TaskGroup
from typing import Final

from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.document_models import StoneSearchDocument
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.stones.rrf import fuse_stone_results
from stone_shelter_assistant.search.stones.search_contracts import (
    HybridSearchResult,
    HybridSearchSettings,
    StoneSearchFilters,
)

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

    async def search_hybrid(
        self,
        lexical_query: str,
        semantic_query: str,
        filters: StoneSearchFilters | None = None,
        settings: HybridSearchSettings | None = None,
    ) -> HybridSearchResult:
        """Run both card searches concurrently, then fuse their complete results.

        TaskGroup cancels the sibling on failure and propagates an ExceptionGroup;
        a failed engine must not be mistaken for an empty successful result.
        """
        lexical_query, semantic_query = lexical_query.strip(), semantic_query.strip()
        if not lexical_query or not semantic_query:
            raise ValueError("Hybrid search requires both lexical and semantic queries")
        settings = HybridSearchSettings() if settings is None else settings

        async def lexical_search(_: dict[str, object]) -> list[StoneSearchDocument]:
            return await self.search_lexical(lexical_query, filters, settings.per_engine_limit)

        async def semantic_search(_: dict[str, object]) -> list[StoneSearchDocument]:
            return await self.search_semantic(semantic_query, filters, settings.per_engine_limit)

        parameters: dict[str, object] = {
            "filters": filters.model_dump(mode="json") if filters else {},
            "limit": settings.per_engine_limit,
        }
        async with TaskGroup() as group:
            lexical = group.create_task(
                RunnableLambda(lexical_search, name="typesense_search").ainvoke(
                    {**parameters, "query": lexical_query}
                )
            )
            semantic = group.create_task(
                RunnableLambda(semantic_search, name="qdrant_search").ainvoke(
                    {
                        **parameters,
                        "query": semantic_query,
                        "embedding_model": getattr(
                            self._embeddings, "model", type(self._embeddings).__name__
                        ),
                    }
                )
            )

        def fusion(_: dict[str, object]) -> HybridSearchResult:
            return fuse_stone_results(lexical.result(), semantic.result(), settings)

        return await RunnableLambda(fusion, name="rrf_fusion").ainvoke(
            {
                "lexical_ids": [str(card.id) for card in lexical.result()],
                "semantic_ids": [str(card.id) for card in semantic.result()],
                "settings": settings.model_dump(mode="json"),
            }
        )

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
