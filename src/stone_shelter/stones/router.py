"""Register a stone and its accompanying case through the HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from stone_shelter.dependencies import (
    get_register_stone_service,
    get_stone_indexing_service,
)
from stone_shelter.search.stones.stone_indexing_service import StoneIndexingService
from stone_shelter.stones.api_contracts import (
    StoneRegistrationRequest,
    StoneRegistrationResponse,
)
from stone_shelter.stones.service import RegisterStoneService

router = APIRouter(prefix="/api/v1/stones", tags=["stones"])


@router.post(
    "",
    response_model=StoneRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_stone(
    request: StoneRegistrationRequest,
    register_stone_service: Annotated[RegisterStoneService, Depends(get_register_stone_service)],
    indexing_stone_service: Annotated[StoneIndexingService, Depends(get_stone_indexing_service)],
) -> StoneRegistrationResponse:
    created_id = await register_stone_service.register(request)

    # NOTE: Learning-project happy path. Retry and recovery are intentionally omitted.
    await indexing_stone_service.index(created_id)

    return StoneRegistrationResponse(id=created_id)
