"""Request contracts for assistant questions."""

from typing import Literal

from pydantic import Field, model_validator

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
    comparison_id: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{1,110}$")
    run_number: int | None = Field(default=None, ge=1)
    source_hash: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def require_comparison_run_identity(self) -> "QuestionRequest":
        if (self.comparison_id is None) != (self.run_number is None):
            raise ValueError("comparison_id and run_number must be provided together")
        return self
