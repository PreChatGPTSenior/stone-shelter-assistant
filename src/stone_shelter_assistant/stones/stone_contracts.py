"""Typed PostgreSQL read models for a stone's complete card and current case."""

from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict

from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    CareLevel,
    SocializationTrait,
    StoneSize,
    StoneType,
)


class StoneProfileDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    socialization_traits: list[SocializationTrait]
    care_level: CareLevel | None
    health_notes: str | None
    trigger_notes: str | None
    preferred_environment: str | None


class ShelterCaseDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: UUID
    case_number: str
    adoption_status: AdoptionStatus
    current_shelter_id: UUID
    admission_date: AwareDatetime


class StoneDetails(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    external_id: UUID
    name: str
    stone_type: StoneType
    stone_size: StoneSize
    biography: str | None
    profile: StoneProfileDetails | None
    shelter_case: ShelterCaseDetails
