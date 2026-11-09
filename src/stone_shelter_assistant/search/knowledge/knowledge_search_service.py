"""Search the encyclopedia and compatibility guide."""

from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    KNOWLEDGE_DOCUMENT_ADAPTER,
    CompatibilityPairSearchDocument,
    KnowledgeDocument,
    KnowledgeSearchFilters,
)
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.enums import StoneType


class KnowledgeSearchService:
    def __init__(
        self, typesense: AsyncClient, qdrant: AsyncQdrantClient, embeddings: Embeddings
    ) -> None:
        self._typesense = typesense
        self._qdrant = qdrant
        self._embeddings = embeddings

    async def search_lexical(
        self, query: str = "", filters: KnowledgeSearchFilters | None = None, limit: int = 5
    ) -> list[KnowledgeDocument]:
        return await self._search_lexical(query, _exact_matches(filters), limit)

    async def search_semantic(
        self, query: str, filters: KnowledgeSearchFilters | None = None, limit: int = 5
    ) -> list[KnowledgeDocument]:
        query = query.strip()
        if not query:
            raise ValueError("Semantic search requires a query")

        matches = _exact_matches(filters)
        result = await self._qdrant.query_points(
            collection_name=qdrant_collections.KNOWLEDGE_COLLECTION,
            query=await self._embeddings.aembed_query(query),
            query_filter=models.Filter(
                must=[
                    models.FieldCondition(key=field, match=models.MatchValue(value=value))
                    for field, value in matches
                ]
            )
            if matches
            else None,
            limit=limit,
            with_payload=True,
        )
        return [
            KNOWLEDGE_DOCUMENT_ADAPTER.validate_python({**(point.payload or {}), "id": point.id})
            for point in result.points
        ]

    async def get_compatibility_pair(
        self, first_type: StoneType, second_type: StoneType, language: str = DEFAULT_LANGUAGE
    ) -> CompatibilityPairSearchDocument | None:
        filters = KnowledgeSearchFilters(
            document_kind=DocumentKind.COMPATIBILITY_PAIR, language=language
        )
        matches = [*_exact_matches(filters), ("pair_key", build_pair_key(first_type, second_type))]
        documents = await self._search_lexical("", matches, limit=1)
        if not documents:
            return None
        pair = documents[0]
        if not isinstance(pair, CompatibilityPairSearchDocument):
            raise ValueError("Expected a compatibility pair document")
        return pair

    async def _search_lexical(
        self, query: str, matches: list[tuple[str, str]], limit: int
    ) -> list[KnowledgeDocument]:
        documents = self._typesense.collections[
            typesense_collections.KNOWLEDGE_COLLECTION
        ].documents
        result = await documents.search(
            {
                "q": query.strip() or "*",
                "query_by": "title,text",
                "filter_by": " && ".join(f"{field}:=`{value}`" for field, value in matches),
                "per_page": limit,
            }
        )
        return [
            KNOWLEDGE_DOCUMENT_ADAPTER.validate_python(hit["document"])
            for hit in result.get("hits", [])
        ]


def _exact_matches(filters: KnowledgeSearchFilters | None) -> list[tuple[str, str]]:
    matches: list[tuple[str, str]] = []
    if filters is None:
        return matches
    if filters.document_kind is not None:
        matches.append(("document_kind", filters.document_kind.value))
    if filters.stone_type is not None:
        matches.append(("stone_types", filters.stone_type.value))
    if filters.language is not None:
        matches.append(("language", filters.language))
    return matches
