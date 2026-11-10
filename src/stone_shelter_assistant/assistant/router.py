"""HTTP entry point for assistant questions."""

from typing import Annotated

from fastapi import APIRouter, Depends

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.dependencies import QuestionWorkflow, get_question_workflow

router = APIRouter(prefix="/api/v1", tags=["assistant"])


@router.post("/questions")
async def ask_question(
    payload: QuestionRequest,
    workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)],
) -> dict[str, object]:
    return await workflow(payload)
