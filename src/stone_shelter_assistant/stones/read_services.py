"""Read stone cards and shelter cases for the assistant."""

from collections.abc import Sequence
from uuid import UUID

from stone_shelter_assistant.stones.repository_protocols import (
    ShelterCaseRepository,
    StoneRepository,
)
from stone_shelter_assistant.stones.stone_case_state import StoneCaseState
from stone_shelter_assistant.stones.stone_contracts import NamedStoneStatus, StoneDetails


class StoneReadService:
    def __init__(self, stones: StoneRepository, cases: ShelterCaseRepository) -> None:
        self._stones = stones
        self._cases = cases

    async def get_details(
        self,
        *,
        stone_id: UUID | None = None,
        stone_external_id: UUID | None = None,
    ) -> StoneDetails | None:
        return await self._stones.get_details(
            stone_id=stone_id,
            stone_external_id=stone_external_id,
        )

    async def get_current_states(self, stone_ids: Sequence[UUID]) -> list[StoneCaseState]:
        return await self._cases.get_current_states(stone_ids)

    async def get_status_by_name(self, name: str) -> list[NamedStoneStatus]:
        return await self._stones.get_status_by_name(name)

    async def get_case_timeline(self, case_external_id: UUID) -> list[dict[str, str]]:
        events = await self._cases.get_case_timeline(case_external_id)
        return [
            {
                "event_external_id": str(event.external_id),
                "event_type": event.event_type,
                "occurred_at": event.occurred_at.isoformat(),
                "event_notes": event.event_notes,
            }
            for event in events
        ]
