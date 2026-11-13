"""HTTP entry point for assistant questions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Response

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.dependencies import QuestionWorkflow, get_question_workflow

router = APIRouter(prefix="/api/v1", tags=["assistant"])


@router.post("/questions")
async def ask_question(
    payload: QuestionRequest,
    response: Response,
    workflow: Annotated[QuestionWorkflow, Depends(get_question_workflow)],
    session_id: Annotated[
        str,
        Header(alias="X-Session-ID", max_length=128, pattern=r"^STPY-[A-Za-z0-9._-]+$"),
    ],
) -> dict[str, object]:
    user_id = "STPY-local-test-user"
    result = await workflow(payload, user_id, session_id)
    response.headers["X-Session-ID"] = session_id
    return result
