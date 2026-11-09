"""Current operational state of a stone in its shelter case."""

from dataclasses import dataclass
from uuid import UUID

from stone_shelter_assistant.stones.enums import AdoptionStatus


@dataclass(frozen=True, slots=True)
class StoneCaseState:
    stone_id: UUID
    adoption_status: AdoptionStatus
    current_shelter_id: UUID
