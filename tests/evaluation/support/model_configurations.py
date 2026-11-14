"""Named model settings shared by full workflow and isolated evidence tests.

EVALUATION_MODEL_CONFIGURATIONS contains a JSON list. model_id selects the main
workflow model, evaluation_model_id selects grounding/evidence extraction.
Isolated candidate assessment uses evaluation_model_id only. Configurations must
be nonempty and uniquely named; no previous environment format is accepted.
"""

import os
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, TypeAdapter


class ModelConfiguration(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    name: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    model_id: str = Field(default="openai/gpt-5.6-luna", min_length=1)
    evaluation_model_id: str = Field(default="openai/gpt-5.6-terra", min_length=1)
    reasoning_effort: Literal["none", "low", "medium", "high", "xhigh", "max"] = "medium"
    max_tokens: int = Field(default=8192, ge=1)


def model_configurations() -> list[ModelConfiguration]:
    raw = os.getenv("EVALUATION_MODEL_CONFIGURATIONS")
    configurations = (
        TypeAdapter(list[ModelConfiguration]).validate_json(raw)
        if raw is not None
        else [ModelConfiguration(name="luna56-terra56")]
    )
    if not configurations or len({item.name for item in configurations}) != len(configurations):
        raise ValueError("Model configurations must have unique names and must not be empty")
    return configurations
