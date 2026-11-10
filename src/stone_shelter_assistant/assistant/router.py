"""HTTP entry point for future assistant questions."""

from fastapi import APIRouter, HTTPException, status

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest

router = APIRouter(prefix="/api/v1", tags=["assistant"])


@router.post("/questions", status_code=status.HTTP_501_NOT_IMPLEMENTED)
async def ask_question(_payload: QuestionRequest) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Question answering is not implemented yet.",
    )
