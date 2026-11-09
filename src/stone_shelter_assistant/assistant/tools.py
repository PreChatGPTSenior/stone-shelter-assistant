"""Build the assistant's read-only stone tools."""

from typing import Annotated
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from stone_shelter_assistant.search.stones.search_contracts import StoneSearchFilters
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.repository_protocols import ShelterCaseRepository


def stone_search_tools(search: StoneSearchService, cases: ShelterCaseRepository) -> list[BaseTool]:
    @tool
    async def search_stones_lexical(
        query: str = "",
        filters: StoneSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Find stone cards by name, profile text, or exact filters. Omit text for filter-only search."""
        return [
            card.model_dump(mode="json")
            for card in await search.search_lexical(query, filters, limit)
        ]

    @tool
    async def search_stones_semantic(
        query: Annotated[str, Field(min_length=1)],
        filters: StoneSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Find stone cards whose profiles match a natural-language description."""
        return [
            card.model_dump(mode="json")
            for card in await search.search_semantic(query, filters, limit)
        ]

    @tool
    async def get_current_stone_statuses(
        stone_ids: Annotated[list[UUID], Field(min_length=1, max_length=20)],
    ) -> list[dict[str, str]]:
        """Check current adoption status and shelter in PostgreSQL using stone card IDs."""
        return [
            {
                "stone_id": str(state.stone_id),
                "adoption_status": state.adoption_status.value,
                "current_shelter_id": str(state.current_shelter_id),
            }
            for state in await cases.get_current_states(stone_ids)
        ]

    return [search_stones_lexical, search_stones_semantic, get_current_stone_statuses]
