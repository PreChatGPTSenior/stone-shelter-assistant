"""Explicit HTTP operations for reloading the authored knowledge sources."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from stone_shelter_assistant.dependencies import get_grounding_catalog, get_knowledge_indexer
from stone_shelter_assistant.search.knowledge.grounding_catalog import (
    GroundingCatalog,
    GroundingEntry,
)
from stone_shelter_assistant.search.knowledge.knowledge_indexer import KnowledgeIndexer

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/grounding/reload")
async def reload_grounding(
    catalog: Annotated[GroundingCatalog, Depends(get_grounding_catalog)],
) -> dict[str, object]:
    seed = Path("fixtures/knowledge/grounding") / f"grounding_{catalog.version}.json"
    snapshot = await catalog.reload(seed)
    return {
        "count": len(snapshot.entries),
        "content_hash": snapshot.content_hash,
        "catalog_version": snapshot.catalog_version,
    }


@router.get("/grounding/search")
async def search_grounding(
    q: str, catalog: Annotated[GroundingCatalog, Depends(get_grounding_catalog)]
) -> list[GroundingEntry]:
    return await catalog.search(q)


@router.put("/grounding/entries/{entry_id}")
async def update_grounding(
    entry_id: str,
    entry: GroundingEntry,
    catalog: Annotated[GroundingCatalog, Depends(get_grounding_catalog)],
) -> dict[str, object]:
    if entry_id != entry.id:
        raise HTTPException(status_code=422, detail="Entry ID does not match the path")
    try:
        snapshot = await catalog.upsert(entry)
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return {"count": len(snapshot.entries), "content_hash": snapshot.content_hash}


@router.post("/encyclopedia/reindex")
async def reindex_encyclopedia(
    indexer: Annotated[KnowledgeIndexer, Depends(get_knowledge_indexer)],
) -> dict[str, int]:
    # NOTE: Learning-project happy path. Delete and reload without compatibility checks or rollback.
    return {"indexed_encyclopedia_documents": await indexer.reload_encyclopedia()}


@router.post("/compatibility/reindex")
async def reindex_compatibility(
    indexer: Annotated[KnowledgeIndexer, Depends(get_knowledge_indexer)],
) -> dict[str, int]:
    # NOTE: Learning-project happy path. Delete and reload without compatibility checks or rollback.
    return {"indexed_compatibility_documents": await indexer.reload_compatibility()}
