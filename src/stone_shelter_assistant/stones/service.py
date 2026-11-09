"""Register one stone, its case, optional profile, and supplied history."""

from uuid import UUID

from stone_shelter_assistant.core.unit_of_work import UnitOfWork
from stone_shelter_assistant.stones.api_contracts import StoneRegistrationRequest
from stone_shelter_assistant.stones.models import (
    CaseEventModel,
    ShelterCaseModel,
    StoneModel,
    StoneProfileModel,
)
from stone_shelter_assistant.stones.repository_protocols import StoneRepository


class RegisterStoneService:
    def __init__(self, repository: StoneRepository, uow: UnitOfWork) -> None:
        self._repository = repository
        self._uow = uow

    async def register(self, request: StoneRegistrationRequest) -> UUID:
        stone = StoneModel(
            **request.stone.model_dump(exclude={"stone_type", "stone_size"}),
            stone_type=request.stone.stone_type.value,
            stone_size=request.stone.stone_size.value,
        )

        if request.profile is not None:
            profile_request = request.profile
            stone.profile = StoneProfileModel(
                **profile_request.model_dump(exclude={"socialization_traits", "care_level"}),
                socialization_traits=sorted(
                    trait.value for trait in profile_request.socialization_traits
                ),
                care_level=(
                    profile_request.care_level.value
                    if profile_request.care_level is not None
                    else None
                ),
            )

        stone.shelter_case = ShelterCaseModel(
            **request.shelter_case.model_dump(exclude={"events", "adoption_status"}),
            adoption_status=request.shelter_case.adoption_status.value,
            events=[
                CaseEventModel(
                    **event.model_dump(exclude={"event_type"}),
                    event_type=event.event_type.value,
                )
                for event in request.shelter_case.events
            ],
        )

        self._repository.add(stone)
        await self._uow.commit()
        return stone.id
