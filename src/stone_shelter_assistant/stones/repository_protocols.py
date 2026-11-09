"""Repository operations used by stone registration and search indexing."""

from collections.abc import Sequence
from typing import Protocol
from uuid import UUID

from stone_shelter_assistant.stones.models import CaseEventModel, ShelterCaseModel, StoneModel
from stone_shelter_assistant.stones.stone_case_state import StoneCaseState


class StoneRepository(Protocol):
    def add(self, stone: StoneModel) -> None: ...
    async def get_by_id(self, stone_id: UUID) -> StoneModel | None: ...


class ShelterCaseRepository(Protocol):
    async def get_by_stone_id(self, stone_id: UUID) -> ShelterCaseModel | None: ...
    async def get_current_states(self, stone_ids: Sequence[UUID]) -> list[StoneCaseState]: ...
    async def get_case_timeline(self, case_external_id: UUID) -> list[CaseEventModel]: ...
