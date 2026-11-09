"""Repository operations used by catalog application scenarios."""

from typing import Protocol
from uuid import UUID

from stone_shelter.adoption.persistence.models import ShelterCaseModel
from stone_shelter.catalog.persistence.models import StoneModel


class StoneRepository(Protocol):
    def add(self, stone: StoneModel) -> None: ...
    async def get_by_id(self, stone_id: UUID) -> StoneModel | None: ...


class ShelterCaseRepository(Protocol):
    async def get_by_stone_id(self, stone_id: UUID) -> ShelterCaseModel | None: ...
