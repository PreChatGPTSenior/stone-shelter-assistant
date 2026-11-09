"""Input models for stone search."""

from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    CareLevel,
    SocializationTrait,
    StoneSize,
    StoneType,
)

type FilterText = Annotated[str, Field(min_length=1, pattern=r"^[^`]+$")]


class StoneSearchFilters(BaseModel):
    """Exact filters on indexed stone cards."""

    model_config = ConfigDict(extra="forbid")

    stone_external_id: UUID | None = None
    case_external_id: UUID | None = None
    case_number: FilterText | None = None
    stone_type: StoneType | None = None
    stone_size: StoneSize | None = None
    current_shelter_id: UUID | None = None
    adoption_status: AdoptionStatus | None = None
    care_level: CareLevel | None = None
    language: FilterText | None = None
    socialization_traits: list[SocializationTrait] = Field(
        default_factory=list, description="Require every listed trait."
    )
