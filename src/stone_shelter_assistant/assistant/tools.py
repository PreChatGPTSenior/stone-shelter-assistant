"""Build the assistant's read-only search and lookup tools."""

from typing import Annotated
from uuid import UUID

from langchain_core.tools import BaseTool, tool
from pydantic import Field

from stone_shelter_assistant.search.document_models import (
    DEFAULT_LANGUAGE,
    KnowledgeLanguage,
    KnowledgeSearchFilters,
)
from stone_shelter_assistant.search.enums import CompatibilityVerdict
from stone_shelter_assistant.search.knowledge.knowledge_search_service import KnowledgeSearchService
from stone_shelter_assistant.search.stones.case_event_search_service import CaseEventSearchService
from stone_shelter_assistant.search.stones.search_contracts import (
    CaseEventSearchFilters,
    StoneSearchFilters,
)
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.stones.enums import StoneType
from stone_shelter_assistant.stones.read_services import StoneReadService


def stone_lookup_tools(stones: StoneReadService) -> list[BaseTool]:
    @tool
    async def get_stone_details(
        stone_id: UUID | None = None,
        stone_external_id: UUID | None = None,
    ) -> dict[str, object] | None:
        """Read a stone, optional profile, and current case from PostgreSQL.

        Provide exactly one ID: stone_id is a stone card's internal id;
        stone_external_id is the external stone ID available in cards and events.
        Returns None when the stone does not exist. Use get_case_timeline with
        shelter_case.external_id to read its history separately.
        """
        details = await stones.get_details(stone_id=stone_id, stone_external_id=stone_external_id)
        return details.model_dump(mode="json") if details is not None else None

    @tool
    async def get_stone_status_by_name(name: str) -> list[dict[str, object]]:
        """Read current PostgreSQL status and type by exact name, returning up to two matches."""
        return [item.model_dump(mode="json") for item in await stones.get_status_by_name(name)]

    return [get_stone_details, get_stone_status_by_name]


def stone_search_tools(search: StoneSearchService, stones: StoneReadService) -> list[BaseTool]:
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
            for state in await stones.get_current_states(stone_ids)
        ]

    return [search_stones_lexical, search_stones_semantic, get_current_stone_statuses]


def case_event_search_tools(
    search: CaseEventSearchService, stones: StoneReadService
) -> list[BaseTool]:
    @tool
    async def search_case_events_lexical(
        query: str = "",
        filters: CaseEventSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Find matching words in case event notes. Omit text for filter-only search."""
        return [
            event.model_dump(mode="json")
            for event in await search.search_lexical(query, filters, limit)
        ]

    @tool
    async def search_case_events_semantic(
        query: Annotated[str, Field(min_length=1)],
        filters: CaseEventSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Find case event notes that match a natural-language description."""
        return [
            event.model_dump(mode="json")
            for event in await search.search_semantic(query, filters, limit)
        ]

    @tool
    async def get_case_timeline(case_external_id: UUID) -> list[dict[str, str]]:
        """Read the complete chronological history of a known case by its external ID."""
        return await stones.get_case_timeline(case_external_id)

    return [search_case_events_lexical, search_case_events_semantic, get_case_timeline]


def knowledge_search_tools(search: KnowledgeSearchService) -> list[BaseTool]:
    @tool
    async def search_knowledge_lexical(
        query: str = "",
        filters: KnowledgeSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Search reference titles and text for matching words or exact filters."""
        return [
            document.model_dump(mode="json")
            for document in await search.search_lexical(query, filters, limit)
        ]

    @tool
    async def search_knowledge_semantic(
        query: Annotated[str, Field(min_length=1)],
        filters: KnowledgeSearchFilters | None = None,
        limit: Annotated[int, Field(ge=1, le=20)] = 5,
    ) -> list[dict[str, object]]:
        """Find encyclopedia or compatibility evidence matching a description."""
        return [
            document.model_dump(mode="json")
            for document in await search.search_semantic(query, filters, limit)
        ]

    @tool
    async def get_compatibility_pair(
        first_type: StoneType,
        second_type: StoneType,
        language: KnowledgeLanguage = DEFAULT_LANGUAGE,
    ) -> dict[str, object] | None:
        """Look up the authored compatibility verdict and advice for exactly two stone types."""
        pair = await search.get_compatibility_pair(first_type, second_type, language)
        return pair.model_dump(mode="json") if pair is not None else None

    @tool
    async def list_compatibility_pairs(
        stone_type: StoneType, verdict: CompatibilityVerdict
    ) -> list[dict[str, object]]:
        """List authored compatibility rules for one type and the exact verdict."""
        return [
            pair.model_dump(mode="json")
            for pair in await search.list_compatibility_pairs(stone_type, verdict)
        ]

    return [
        search_knowledge_lexical,
        search_knowledge_semantic,
        get_compatibility_pair,
        list_compatibility_pairs,
    ]
