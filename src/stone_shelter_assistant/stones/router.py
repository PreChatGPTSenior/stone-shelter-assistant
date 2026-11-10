"""Register a stone and its accompanying case through the HTTP API."""

from typing import Annotated

from fastapi import APIRouter, Depends, status

from stone_shelter_assistant.dependencies import get_stone_ingestion_service
from stone_shelter_assistant.stones.api_contracts import (
    StoneRegistrationRequest,
    StoneRegistrationResponse,
)
from stone_shelter_assistant.stones.service import StoneIngestionService

router = APIRouter(prefix="/api/v1/stones", tags=["stones"])


@router.post(
    "",
    response_model=StoneRegistrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_stone(
    request: StoneRegistrationRequest,
    ingestion: Annotated[StoneIngestionService, Depends(get_stone_ingestion_service)],
) -> StoneRegistrationResponse:
    return StoneRegistrationResponse(id=await ingestion.ingest(request))
