"""Access stones and shelter cases through the current database session."""

from collections.abc import Sequence
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from stone_shelter_assistant.stones.enums import AdoptionStatus
from stone_shelter_assistant.stones.models import CaseEventModel, ShelterCaseModel, StoneModel
from stone_shelter_assistant.stones.stone_case_state import StoneCaseState
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus, StoneDetails


class SqlAlchemyStoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, stone: StoneModel) -> None:
        self._session.add(stone)

    async def get_by_id(self, stone_id: UUID) -> StoneModel | None:
        return await self._session.get(
            StoneModel, stone_id, options=[selectinload(StoneModel.profile)]
        )

    async def get_details(
        self, *, stone_id: UUID | None = None, stone_external_id: UUID | None = None
    ) -> StoneDetails | None:
        """Read a current card using exactly one internal or external stone ID."""
        if (stone_id is None) == (stone_external_id is None):
            raise ValueError("Provide exactly one of stone_id or stone_external_id")
        identity = (
            StoneModel.id == stone_id
            if stone_id is not None
            else StoneModel.external_id == stone_external_id
        )
        statement = (
            select(StoneModel)
            .where(identity)
            .options(selectinload(StoneModel.profile), selectinload(StoneModel.shelter_case))
            .execution_options(populate_existing=True)
        )
        stone = await self._session.scalar(statement)
        return StoneDetails.model_validate(stone) if stone is not None else None

    async def get_status_by_name(self, name: str) -> list[NamedStoneStatus]:
        """Read current status in one query and return at most two matches to detect ambiguity."""
        statement = (
            select(
                StoneModel.id.label("stone_id"),
                StoneModel.name,
                StoneModel.stone_type,
                ShelterCaseModel.adoption_status,
            )
            .join(StoneModel.shelter_case)
            .where(func.lower(StoneModel.name) == func.lower(name.strip()))
            .order_by(StoneModel.id)
            .limit(2)
        )
        rows = await self._session.execute(statement)
        return [NamedStoneStatus.model_validate(row) for row in rows.mappings()]


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
