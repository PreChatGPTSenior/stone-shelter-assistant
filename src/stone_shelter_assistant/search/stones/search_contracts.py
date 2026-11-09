"""Input models for stone search."""

from typing import Annotated, Self
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    CareLevel,
    CaseEventType,
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


class CaseEventSearchFilters(BaseModel):
    """Filters shared by both case event search methods."""

    model_config = ConfigDict(extra="forbid")

    stone_external_id: UUID | None = None
    event_type: CaseEventType | None = None
    occurred_from: AwareDatetime | None = Field(default=None, description="Inclusive start.")
    occurred_before: AwareDatetime | None = Field(default=None, description="Exclusive end.")

    @model_validator(mode="after")
    def validate_date_range(self) -> Self:
        if (
            self.occurred_from is not None
            and self.occurred_before is not None
            and self.occurred_from >= self.occurred_before
        ):
            raise ValueError("occurred_from must be earlier than occurred_before")
        return self
