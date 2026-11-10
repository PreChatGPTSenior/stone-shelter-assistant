"""Request contracts for assistant questions."""

from pydantic import Field

from stone_shelter_assistant.core.api_base_models import ApiRequest


class QuestionRequest(ApiRequest):
    question: str = Field(min_length=1)
    model_id: str | None = Field(default=None, min_length=1)
    eval_case_id: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9._:-]{1,128}$")
    fixture_version: str | None = Field(default=None, pattern=r"^[a-zA-Z0-9._:-]{1,128}$")
