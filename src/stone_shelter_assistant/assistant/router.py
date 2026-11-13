"""HTTP entry point for assistant questions."""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Response

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
    if payload.comparison_id is not None and payload.run_number is not None:
        expected_session_id = f"STPY-{payload.comparison_id}-r{payload.run_number:02d}"
        if session_id != expected_session_id:
            raise HTTPException(
                status_code=422,
                detail="X-Session-ID must match the comparison ID and run number",
            )
    user_id = "STPY-local-test-user"
    result = await workflow(payload, user_id, session_id)
    response.headers["X-Session-ID"] = session_id
    return result
