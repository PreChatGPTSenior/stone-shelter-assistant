"""Exercise concurrent backend orchestration without external services."""

import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest
from langchain_core.callbacks import AsyncCallbackHandler
from langchain_core.runnables import RunnableLambda
from pydantic import ValidationError
from qdrant_client.http.exceptions import ResponseHandlingException
from tests.unit.search.test_rrf import card
from typesense.exceptions import ServiceUnavailable

from stone_shelter_assistant.assistant.tools import stone_search_tools
from stone_shelter_assistant.search.stones.search_contracts import (
    HybridSearchSettings,
    StoneSearchFilters,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.enums import AdoptionStatus, StoneType


class RetrievalRecorder(AsyncCallbackHandler):
    def __init__(self) -> None:
        self.outputs: list[Any] = []

    async def on_chain_end(self, outputs: Any, **kwargs: Any) -> None:
        self.outputs.append(outputs)


def clients() -> tuple[Any, Any, Any, Any]:
    documents = SimpleNamespace(search=AsyncMock(return_value={"hits": []}))
    typesense = SimpleNamespace(collections={"stones": SimpleNamespace(documents=documents)})
    qdrant = SimpleNamespace(query_points=AsyncMock(return_value=SimpleNamespace(points=[])))
    embeddings = SimpleNamespace(aembed_query=AsyncMock(return_value=[1.0, 0.0]))
    return typesense, qdrant, embeddings, documents


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-FLOW-02")
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
    assert result.degraded is False
    assert result.failures == []
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
@pytest.mark.acceptance("AC-FLOW-02")
async def test_programming_error_propagates_and_cancels_sibling(failed_engine: str) -> None:
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
@pytest.mark.parametrize("failed_engine", ["lexical", "semantic"])
@pytest.mark.parametrize("has_results", [True, False])
async def test_operational_failure_keeps_successful_engine_and_traces_safe_reason(
    failed_engine: str,
    has_results: bool,
) -> None:
    typesense, qdrant, embeddings, _ = clients()
    service = StoneSearchService(typesense, qdrant, embeddings)
    survivor = card(1)
    lexical_started, semantic_started = asyncio.Event(), asyncio.Event()

    async def lexical(*args: Any) -> Any:
        lexical_started.set()
        await semantic_started.wait()
        if failed_engine == "lexical":
            raise ServiceUnavailable("secret-response-body")
        return [survivor] if has_results else []

    async def semantic(*args: Any) -> Any:
        semantic_started.set()
        await lexical_started.wait()
        if failed_engine == "semantic":
            raise ResponseHandlingException(httpx.ConnectError("secret-response-body"))
        return [survivor] if has_results else []

    service.search_lexical = AsyncMock(side_effect=lexical)  # type: ignore[method-assign]
    service.search_semantic = AsyncMock(side_effect=semantic)  # type: ignore[method-assign]
    recorder = RetrievalRecorder()

    async def invoke(_: Any) -> Any:
        return await service.search_hybrid("granite", "quiet")

    result = await asyncio.wait_for(
        RunnableLambda(invoke).ainvoke({}, config={"callbacks": [recorder]}),
        2,
    )
    assert [hit.card.id for hit in result.candidates] == ([survivor.id] if has_results else [])
    assert result.degraded is True
    expected = {
        "engine": "typesense" if failed_engine == "lexical" else "qdrant",
        "reason": "service_unavailable" if failed_engine == "lexical" else "transport_error",
    }
    assert [failure.model_dump() for failure in result.failures] == [expected]
    if has_results:
        assert result.candidates[0].lexical_rank == (None if failed_engine == "lexical" else 1)
        assert result.candidates[0].semantic_rank == (None if failed_engine == "semantic" else 1)
    service.search_lexical.assert_awaited_once()
    service.search_semantic.assert_awaited_once()
    assert "secret-response-body" not in result.model_dump_json()
    assert any(getattr(output, "degraded", False) for output in recorder.outputs)


@pytest.mark.asyncio
async def test_both_operational_failures_remain_an_error() -> None:
    typesense, qdrant, embeddings, documents = clients()
    documents.search.side_effect = ServiceUnavailable("secret-response-body")
    qdrant.query_points.side_effect = ResponseHandlingException(httpx.ConnectError("secret"))
    with pytest.raises(RuntimeError, match="Both hybrid search engines failed"):
        await StoneSearchService(typesense, qdrant, embeddings).search_hybrid("granite", "quiet")
    documents.search.assert_awaited_once()
    qdrant.query_points.assert_awaited_once()


@pytest.mark.asyncio
async def test_invalid_backend_payload_is_not_degraded() -> None:
    typesense, qdrant, embeddings, documents = clients()
    documents.search.return_value = {"hits": [{"document": {"id": "invalid"}}]}
    with pytest.raises(ExceptionGroup) as caught:
        await StoneSearchService(typesense, qdrant, embeddings).search_hybrid("granite", "quiet")
    assert any(isinstance(error, ValidationError) for error in caught.value.exceptions)


@pytest.mark.asyncio
async def test_cancelled_backend_is_not_degraded() -> None:
    typesense, qdrant, embeddings, documents = clients()
    documents.search.side_effect = asyncio.CancelledError()
    with pytest.raises(asyncio.CancelledError):
        await StoneSearchService(typesense, qdrant, embeddings).search_hybrid("granite", "quiet")


@pytest.mark.asyncio
@pytest.mark.parametrize("queries", [(" ", "quiet"), ("granite", " ")])
@pytest.mark.acceptance("AC-FLOW-02")
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
@pytest.mark.acceptance("AC-FLOW-02")
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


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [429, 503])
async def test_embedding_service_failure_keeps_lexical_results(status: int) -> None:
    from ollama import ResponseError

    typesense, qdrant, embeddings, documents = clients()
    survivor = card(1)
    documents.search.return_value = {"hits": [{"document": survivor.model_dump(mode="json")}]}
    embeddings.aembed_query.side_effect = ResponseError("private provider body", status)
    result = await StoneSearchService(typesense, qdrant, embeddings).search_hybrid(
        "granite", "quiet"
    )
    assert [hit.card.id for hit in result.candidates] == [survivor.id]
    assert result.degraded
    assert result.failures[0].engine == "qdrant"
    assert result.failures[0].reason == ("rate_limited" if status == 429 else "service_unavailable")
    documents.search.assert_awaited_once()
    embeddings.aembed_query.assert_awaited_once()
    qdrant.query_points.assert_not_awaited()


@pytest.mark.asyncio
async def test_qdrant_wrapped_validation_error_is_not_degraded() -> None:
    typesense, qdrant, embeddings, _ = clients()
    qdrant.query_points.side_effect = ResponseHandlingException(ValueError("invalid response"))
    with pytest.raises(ExceptionGroup) as caught:
        await StoneSearchService(typesense, qdrant, embeddings).search_hybrid("granite", "quiet")
    assert any(isinstance(error, ResponseHandlingException) for error in caught.value.exceptions)
