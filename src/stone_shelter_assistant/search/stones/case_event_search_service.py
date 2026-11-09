"""Search historical case event notes in the operational indexes."""

from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.document_content import to_unix_microseconds
from stone_shelter_assistant.search.document_models import CaseEventSearchDocument
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.stones.search_contracts import CaseEventSearchFilters


class CaseEventSearchService:
    def __init__(
        self, typesense: AsyncClient, qdrant: AsyncQdrantClient, embeddings: Embeddings
    ) -> None:
        self._typesense = typesense
        self._qdrant = qdrant
        self._embeddings = embeddings

    async def search_lexical(
        self, query: str = "", filters: CaseEventSearchFilters | None = None, limit: int = 5
    ) -> list[CaseEventSearchDocument]:
        filters = filters or CaseEventSearchFilters()
        clauses = [f"{field}:=`{value}`" for field, value in _exact_matches(filters)]
        start, end = _timestamp_bounds(filters)
        if start is not None:
            clauses.append(f"occurred_at:>={start}")
        if end is not None:
            clauses.append(f"occurred_at:<{end}")

        documents = self._typesense.collections[
            typesense_collections.OPERATIONAL_COLLECTION
        ].documents
        result = await documents.search(
            {
                "q": query.strip() or "*",
                "query_by": "text",
                "filter_by": " && ".join(clauses),
                "per_page": limit,
            }
        )
        return [
            CaseEventSearchDocument.model_validate(hit["document"])
            for hit in result.get("hits", [])
        ]

    async def search_semantic(
        self, query: str, filters: CaseEventSearchFilters | None = None, limit: int = 5
    ) -> list[CaseEventSearchDocument]:
        query = query.strip()
        if not query:
            raise ValueError("Semantic search requires a query")

        filters = filters or CaseEventSearchFilters()
        conditions: list[models.Condition] = [
            models.FieldCondition(key=field, match=models.MatchValue(value=value))
            for field, value in _exact_matches(filters)
        ]
        start, end = _timestamp_bounds(filters)
        if start is not None or end is not None:
            conditions.append(
                models.FieldCondition(key="occurred_at", range=models.Range(gte=start, lt=end))
            )

        result = await self._qdrant.query_points(
            collection_name=qdrant_collections.OPERATIONAL_COLLECTION,
            query=await self._embeddings.aembed_query(query),
            query_filter=models.Filter(must=conditions),
            limit=limit,
            with_payload=True,
        )
        return [
            CaseEventSearchDocument.model_validate({**(point.payload or {}), "id": point.id})
            for point in result.points
        ]


def _exact_matches(filters: CaseEventSearchFilters) -> list[tuple[str, str]]:
    matches = [("document_kind", DocumentKind.CASE_EVENT.value)]
    if filters.stone_external_id is not None:
        matches.append(("stone_external_id", str(filters.stone_external_id)))
    if filters.event_type is not None:
        matches.append(("event_type", filters.event_type.value))
    return matches


def _timestamp_bounds(filters: CaseEventSearchFilters) -> tuple[int | None, int | None]:
    start = filters.occurred_from
    end = filters.occurred_before
    return (
        to_unix_microseconds(start) if start is not None else None,
        to_unix_microseconds(end) if end is not None else None,
    )
