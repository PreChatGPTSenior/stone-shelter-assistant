"""Request contracts for assistant questions."""

from pydantic import Field

from stone_shelter_assistant.core.api_base_models import ApiRequest


class QuestionRequest(ApiRequest):
    question: str = Field(min_length=1)
