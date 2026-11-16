"""Retrieve stone cards through lexical or vector search."""

from asyncio import TaskGroup
from typing import Final, Literal

import httpx
from langchain_core.embeddings import Embeddings
from langchain_core.runnables import RunnableLambda
from ollama import ResponseError
from qdrant_client import AsyncQdrantClient, models
from qdrant_client.http.exceptions import ResponseHandlingException, UnexpectedResponse
from typesense import AsyncClient
from typesense import exceptions as typesense_errors

from stone_shelter_assistant.search.document_models import StoneSearchDocument
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.stones.rrf import fuse_stone_results
from stone_shelter_assistant.search.stones.search_contracts import (
    HybridSearchResult,
    HybridSearchSettings,
    SearchEngineFailure,
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

        Operational failures retain the successful sibling without retrying.
        Invalid data, programming errors and cancellation still propagate.
        """
        lexical_query, semantic_query = lexical_query.strip(), semantic_query.strip()
        if not lexical_query or not semantic_query:
            raise ValueError("Hybrid search requires both lexical and semantic queries")
        settings = HybridSearchSettings() if settings is None else settings

        failures: list[SearchEngineFailure] = []

        async def lexical_search(_: dict[str, object]) -> list[StoneSearchDocument]:
            try:
                return await self.search_lexical(lexical_query, filters, settings.per_engine_limit)
            except Exception as error:
                reason = _operational_failure_reason(error)
                if reason is None:
                    raise
                failures.append(SearchEngineFailure(engine="typesense", reason=reason))
                return []

        async def semantic_search(_: dict[str, object]) -> list[StoneSearchDocument]:
            try:
                return await self.search_semantic(
                    semantic_query, filters, settings.per_engine_limit
                )
            except Exception as error:
                reason = _operational_failure_reason(error)
                if reason is None:
                    raise
                failures.append(SearchEngineFailure(engine="qdrant", reason=reason))
                return []

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

        failures.sort(key=lambda failure: failure.engine)
        if len(failures) == 2:
            raise RuntimeError("Both hybrid search engines failed operationally")

        def fusion(_: dict[str, object]) -> HybridSearchResult:
            result = fuse_stone_results(lexical.result(), semantic.result(), settings)
            result.degraded = bool(failures)
            result.failures = failures
            return result

        return await RunnableLambda(fusion, name="rrf_fusion").ainvoke(
            {
                "lexical_ids": [str(card.id) for card in lexical.result()],
                "semantic_ids": [str(card.id) for card in semantic.result()],
                "settings": settings.model_dump(mode="json"),
                "degraded": bool(failures),
                "failures": [failure.model_dump(mode="json") for failure in failures],
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


def _operational_failure_reason(
    error: Exception,
) -> Literal["transport_error", "timeout", "service_unavailable", "rate_limited"] | None:
    """Classify known client failures without recording messages or response bodies."""
    if isinstance(error, ResponseHandlingException):
        # Qdrant also wraps response validation errors; those must propagate.
        error = error.source
    if isinstance(error, (httpx.TimeoutException, typesense_errors.Timeout, TimeoutError)):
        return "timeout"
    if isinstance(
        error, (httpx.TransportError, ConnectionError, typesense_errors.HTTPStatus0Error)
    ):
        return "transport_error"
    if isinstance(error, (typesense_errors.ServerError, typesense_errors.ServiceUnavailable)):
        return "service_unavailable"
    if isinstance(error, (httpx.HTTPStatusError, UnexpectedResponse, ResponseError)):
        status = (
            error.response.status_code
            if isinstance(error, httpx.HTTPStatusError)
            else error.status_code
        )
        if status == 429:
            return "rate_limited"
        if status is not None and status >= 500:
            return "service_unavailable"
    return None
