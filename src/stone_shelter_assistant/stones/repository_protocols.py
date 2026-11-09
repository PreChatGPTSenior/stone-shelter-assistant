"""Repository operations used by stone registration and search indexing."""

from typing import Protocol
from uuid import UUID

from stone_shelter_assistant.stones.models import ShelterCaseModel, StoneModel


class StoneRepository(Protocol):
    def add(self, stone: StoneModel) -> None: ...
    async def get_by_id(self, stone_id: UUID) -> StoneModel | None: ...


class ShelterCaseRepository(Protocol):
    async def get_by_stone_id(self, stone_id: UUID) -> ShelterCaseModel | None: ...
