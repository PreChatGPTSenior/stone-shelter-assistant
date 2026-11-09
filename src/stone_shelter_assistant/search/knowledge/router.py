"""Explicit HTTP operations for reloading the authored knowledge sources."""

from typing import Annotated

from fastapi import APIRouter, Depends

from stone_shelter_assistant.dependencies import get_knowledge_indexer
from stone_shelter_assistant.search.knowledge.knowledge_indexer import KnowledgeIndexer

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


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
