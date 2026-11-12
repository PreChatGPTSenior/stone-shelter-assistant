"""Request contracts for assistant questions."""

from typing import Literal

from pydantic import Field

from stone_shelter_assistant.core.api_base_models import ApiRequest


class QuestionRequest(ApiRequest):
    question: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)
    selection_model_id: str | None = Field(default=None, min_length=1)
    parsing_model_id: str | None = Field(default=None, min_length=1)
    evaluation_model_id: str | None = Field(default=None, min_length=1)
    evaluation_max_tokens: int | None = Field(default=None, ge=1)
    evaluation_reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] | None = (
        None
    )
    answer_model_id: str | None = Field(default=None, min_length=1)
    eval_case_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9._:-]{1,128}$")
    fixture_version: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9._:-]{1,128}$")
