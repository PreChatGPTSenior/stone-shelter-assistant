"""Explicit HTTP operations for reloading the authored knowledge sources."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends

from stone_shelter_assistant.dependencies import get_grounding_catalog, get_knowledge_indexer
from stone_shelter_assistant.search.knowledge.grounding_concept_store_service import (
    GroundingConceptStoreService,
)
from stone_shelter_assistant.search.knowledge.knowledge_indexer import KnowledgeIndexer

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/grounding/reload")
async def reload_grounding(
    catalog: Annotated[GroundingConceptStoreService, Depends(get_grounding_catalog)],
) -> dict[str, object]:
    """Replace the grounding keys in Typesense with its authored fixture."""

    seed = Path("fixtures/knowledge/grounding") / f"grounding_{catalog.version}.json"
    snapshot = await catalog.reload(seed)
    return {
        "count": len(snapshot.entries),
        "content_hash": snapshot.content_hash,
        "catalog_version": snapshot.catalog_version,
    }


@router.post("/encyclopedia/reindex")
async def reindex_encyclopedia(
    indexer: Annotated[KnowledgeIndexer, Depends(get_knowledge_indexer)],
) -> dict[str, int]:
    """Rebuild the encyclopedia projection in Typesense and Qdrant from prepared fixture.

    The injected indexer reads the authored English Markdown encyclopedia, builds
    searchable chapter documents and computes their embeddings.

    This explicit learning-data reload follows a happy path: writes to the two
    backends are not atomic, and a failure is not automatically rolled back.
    """
    return {"indexed_encyclopedia_documents": await indexer.reload_encyclopedia()}


@router.post("/compatibility/reindex")
async def reindex_compatibility(
    indexer: Annotated[KnowledgeIndexer, Depends(get_knowledge_indexer)],
) -> dict[str, int]:
    """Rebuild the compatibility projection in Typesense and Qdrant from prepared fixture.

    The injected indexer turns the authored guide into reading rules, type
    portraits and exact type-pair documents, retaining their explanations and
    conditions.

    This is an explicit happy-path operation with no transaction or automatic rollback across the search engines.
    """
    return {"indexed_compatibility_documents": await indexer.reload_compatibility()}
