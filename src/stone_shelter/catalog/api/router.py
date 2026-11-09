"""Register a stone and its accompanying case through the HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from stone_shelter.api.ingestion_contracts import (
    StoneRegistrationRequest,
    StoneRegistrationResponse,
)
from stone_shelter.application.register_stone import RegisterStoneService
from stone_shelter.bootstrap.dependencies import get_qdrant_stone_indexer, get_register_stone_service, get_typesense_stone_indexer
from stone_shelter.search.qdrant_index import QdrantStoneIndexer
from stone_shelter.search.typesense_index import TypesenseStoneIndexer

router = APIRouter(prefix="/api/v1/stones", tags=["stones"])


@router.post(
    "",
    response_model=StoneRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_stone(
    request: StoneRegistrationRequest,
    service: Annotated[RegisterStoneService, Depends(get_register_stone_service)],
    typesense_indexer: Annotated[TypesenseStoneIndexer, Depends(get_typesense_stone_indexer)],
    qdrant_indexer: Annotated[QdrantStoneIndexer, Depends(get_qdrant_stone_indexer)],
) -> StoneRegistrationResponse:
    created_id = await service.register(request)

    # NOTE: Learning-project happy path. Retry and recovery are intentionally omitted.
    await typesense_indexer.index(created_id)
    await qdrant_indexer.index(created_id)

    return StoneRegistrationResponse(id=created_id)
