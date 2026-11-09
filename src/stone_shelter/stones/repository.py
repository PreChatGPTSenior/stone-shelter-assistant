"""Access stones and shelter cases through the current database session."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from stone_shelter.stones.models import ShelterCaseModel, StoneModel


class SqlAlchemyStoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, stone: StoneModel) -> None:
        self._session.add(stone)

    async def get_by_id(self, stone_id: UUID) -> StoneModel | None:
        return await self._session.get(StoneModel, stone_id)


class SqlAlchemyShelterCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_stone_id(self, stone_id: UUID) -> ShelterCaseModel | None:
        statement = select(ShelterCaseModel).where(ShelterCaseModel.stone_id == stone_id)
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()
