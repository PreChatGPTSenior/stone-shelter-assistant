"""Access stones and shelter cases through the current database session."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stone_shelter_assistant.stones.enums import AdoptionStatus
from stone_shelter_assistant.stones.models import CaseEventModel, ShelterCaseModel, StoneModel
from stone_shelter_assistant.stones.stone_case_state import StoneCaseState


class SqlAlchemyStoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, stone: StoneModel) -> None:
        self._session.add(stone)

    async def get_by_id(self, stone_id: UUID) -> StoneModel | None:
        return await self._session.get(
            StoneModel, stone_id, options=[selectinload(StoneModel.profile)]
        )


class SqlAlchemyShelterCaseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_stone_id(self, stone_id: UUID) -> ShelterCaseModel | None:
        statement = (
            select(ShelterCaseModel)
            .where(ShelterCaseModel.stone_id == stone_id)
            .options(selectinload(ShelterCaseModel.events))
        )
        result = await self._session.execute(statement)
        return result.scalar_one_or_none()

    async def get_current_states(self, stone_ids: Sequence[UUID]) -> list[StoneCaseState]:
        statement = select(
            ShelterCaseModel.stone_id,
            ShelterCaseModel.adoption_status,
            ShelterCaseModel.current_shelter_id,
        ).where(ShelterCaseModel.stone_id.in_(stone_ids))
        rows = await self._session.execute(statement)
        return [
            StoneCaseState(stone_id, AdoptionStatus(status), shelter_id)
            for stone_id, status, shelter_id in rows.tuples()
        ]

    async def get_case_timeline(self, case_external_id: UUID) -> list[CaseEventModel]:
        statement = (
            select(CaseEventModel)
            .join(ShelterCaseModel, CaseEventModel.case_id == ShelterCaseModel.id)
            .where(ShelterCaseModel.external_id == case_external_id)
            .order_by(CaseEventModel.occurred_at, CaseEventModel.external_id)
        )
        return list(await self._session.scalars(statement))
