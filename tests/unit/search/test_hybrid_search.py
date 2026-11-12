"""Exercise concurrent backend orchestration without external services."""

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest

from stone_shelter_assistant.assistant.tools import stone_search_tools
from stone_shelter_assistant.search.stones.search_contracts import (
    HybridSearchSettings,
    StoneSearchFilters,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType


def clients() -> tuple[Any, Any, Any, Any]:
    documents = SimpleNamespace(search=AsyncMock(return_value={"hits": []}))
    typesense = SimpleNamespace(collections={"stones": SimpleNamespace(documents=documents)})
    qdrant = SimpleNamespace(query_points=AsyncMock(return_value=SimpleNamespace(points=[])))
    embeddings = SimpleNamespace(aembed_query=AsyncMock(return_value=[1.0, 0.0]))
    return typesense, qdrant, embeddings, documents


@pytest.mark.asyncio
async def test_hybrid_starts_both_engines_and_shares_filters_and_limits() -> None:
    typesense, qdrant, embeddings, documents = clients()
    lexical_started, semantic_started = asyncio.Event(), asyncio.Event()

    async def lexical_call(params: Any) -> dict[str, Any]:
        lexical_started.set()
        await semantic_started.wait()
        return {"hits": []}

    async def vector_call(**kwargs: Any) -> Any:
        semantic_started.set()
        await lexical_started.wait()
        return SimpleNamespace(points=[])

    documents.search.side_effect = lexical_call
    qdrant.query_points.side_effect = vector_call
    service = StoneSearchService(typesense, qdrant, embeddings)
    filters = StoneSearchFilters(
        stone_type=StoneType.GRANITE, adoption_status=AdoptionStatus.AVAILABLE
    )
    settings = HybridSearchSettings(per_engine_limit=3, pool_limit=2)
    result = await asyncio.wait_for(
        service.search_hybrid(" granite ", " quiet home ", filters, settings), 2
    )
    assert result.candidates == result.dropped == []
    assert result.settings == settings
    lexical_params = documents.search.call_args.args[0]
    assert lexical_params["q"] == "granite"
    assert lexical_params["per_page"] == 3
    assert "document_kind:=`stone`" in lexical_params["filter_by"]
    assert "stone_type:=`GRANITE`" in lexical_params["filter_by"]
    assert "adoption_status:=`AVAILABLE`" in lexical_params["filter_by"]
    vector_params = qdrant.query_points.call_args.kwargs
    assert vector_params["limit"] == 3
    conditions = vector_params["query_filter"].must
    assert {condition.key: condition.match.value for condition in conditions} == {
        "document_kind": "stone",
        "stone_type": "GRANITE",
        "adoption_status": "AVAILABLE",
    }
    embeddings.aembed_query.assert_awaited_once_with("quiet home")
    documents.search.assert_awaited_once()
    qdrant.query_points.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("failed_engine", ["lexical", "semantic"])
async def test_backend_failure_propagates_and_cancels_sibling(failed_engine: str) -> None:
    typesense, qdrant, embeddings, documents = clients()
    sibling_started, sibling_cancelled = asyncio.Event(), asyncio.Event()

    async def fail(*args: Any, **kwargs: Any) -> Any:
        await sibling_started.wait()
        raise RuntimeError("Backend unavailable")

    async def pending(*args: Any, **kwargs: Any) -> Any:
        sibling_started.set()
        try:
            await asyncio.Event().wait()
        finally:
            sibling_cancelled.set()

    documents.search.side_effect = fail if failed_engine == "lexical" else pending
    qdrant.query_points.side_effect = fail if failed_engine == "semantic" else pending
    with pytest.raises(ExceptionGroup) as caught:
        await asyncio.wait_for(
            StoneSearchService(typesense, qdrant, embeddings).search_hybrid("granite", "quiet"), 2
        )
    assert any(isinstance(error, RuntimeError) for error in caught.value.exceptions)
    assert sibling_cancelled.is_set()


@pytest.mark.asyncio
@pytest.mark.parametrize("queries", [(" ", "quiet"), ("granite", " ")])
async def test_empty_query_fails_before_any_backend_or_embedding_call(
    queries: tuple[str, str],
) -> None:
    typesense, qdrant, embeddings, documents = clients()
    with pytest.raises(ValueError, match="requires both"):
        await StoneSearchService(typesense, qdrant, embeddings).search_hybrid(*queries)
    documents.search.assert_not_awaited()
    qdrant.query_points.assert_not_awaited()
    embeddings.aembed_query.assert_not_awaited()


@pytest.mark.asyncio
async def test_hybrid_tool_serializes_result_and_declares_two_backend_calls() -> None:
    typesense, qdrant, embeddings, _ = clients()
    tools = stone_search_tools(StoneSearchService(typesense, qdrant, embeddings), AsyncMock())
    tool = next(item for item in tools if item.name == "search_stones_hybrid")
    result = await tool.ainvoke({"lexical_query": "granite", "semantic_query": "quiet home"})
    assert result["settings"] == {
        "version": "stone-rrf-v1",
        "per_engine_limit": 5,
        "pool_limit": 10,
        "rrf_k": 60,
    }
    assert result["candidates"] == result["dropped"] == []
    assert tool.metadata == {"retrieval_calls": 2}
