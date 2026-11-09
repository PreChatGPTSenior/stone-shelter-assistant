"""Validated requests and responses for registering a stone and its case."""

from uuid import UUID

from pydantic import AwareDatetime, Field, field_validator
from pydantic_core import PydanticCustomError

from stone_shelter_assistant.core.api_base_models import ApiRequest, ApiResponse
from stone_shelter_assistant.stones.enums import (
    AdoptionStatus,
    CareLevel,
    CaseEventType,
    SocializationTrait,
    StoneSize,
    StoneType,
)


class StoneCreateRequest(ApiRequest):
    name: str = Field(min_length=1, max_length=120)
    stone_type: StoneType = Field(alias="stoneType")
    stone_size: StoneSize = Field(alias="stoneSize")
    biography: str | None = Field(default=None, max_length=2048)
    external_id: UUID = Field(alias="externalId")


class StoneProfileCreateRequest(ApiRequest):
    socialization_traits: set[SocializationTrait] = Field(
        default_factory=set,
        alias="socializationTraits",
    )
    care_level: CareLevel | None = Field(default=None, alias="careLevel")
    health_notes: str | None = Field(default=None, alias="healthNotes")
    trigger_notes: str | None = Field(default=None, alias="triggerNotes")
    preferred_environment: str | None = Field(default=None, alias="preferredEnvironment")


class CaseEventCreateRequest(ApiRequest):
    external_id: UUID = Field(alias="externalId")
    event_type: CaseEventType = Field(alias="eventType")
    occurred_at: AwareDatetime = Field(alias="occurredAt")
    event_notes: str = Field(min_length=1, alias="eventNotes")


class ShelterCaseCreateRequest(ApiRequest):
    external_id: UUID = Field(alias="externalId")
    case_number: str = Field(min_length=1, alias="caseNumber")
    current_shelter_id: UUID = Field(alias="currentShelterId")
    adoption_status: AdoptionStatus = Field(alias="adoptionStatus")
    admission_date: AwareDatetime = Field(alias="admissionDate")
    events: list[CaseEventCreateRequest] = Field(min_length=1)

    @field_validator("events")
    @classmethod
    def check_event_limit(
        cls,
        events: list[CaseEventCreateRequest],
    ) -> list[CaseEventCreateRequest]:
        limit = 100
        if len(events) > limit:
            raise PydanticCustomError(
                "CASE_EVENT_LIMIT_EXCEEDED",
                "Case history exceeds the limit of {limit} events.",
                {"limit": limit, "actual": len(events)},
            )
        return events

    @field_validator("events")
    @classmethod
    def require_initial_admission(
        cls,
        events: list[CaseEventCreateRequest],
    ) -> list[CaseEventCreateRequest]:
        if not any(event.event_type is CaseEventType.ADMITTED for event in events):
            raise PydanticCustomError(
                "CASE_ADMITTED_EVENT_REQUIRED",
                "Case events must include {required_event_type}.",
                {"required_event_type": CaseEventType.ADMITTED.value},
            )
        return events


class StoneRegistrationRequest(ApiRequest):
    stone: StoneCreateRequest
    shelter_case: ShelterCaseCreateRequest = Field(alias="shelterCase")
    profile: StoneProfileCreateRequest | None = None


class StoneRegistrationResponse(ApiResponse):
    id: UUID
