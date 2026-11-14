"""Check named reference identity lookup with stubbed storage tools."""

from typing import Any

import pytest
from langchain_core.tools import tool

from stone_shelter_assistant.assistant.reference_lookup import ReferenceTools, read_reference
from stone_shelter_assistant.assistant.tool_planning import (
    ReferenceRequest,
    ToolPlan,
)


@pytest.mark.asyncio
@pytest.mark.acceptance("AC-IDENTITY-01")
async def test_distinct_named_recommendation_lookup_preserves_reference_identity() -> None:
    names = {
        "Svetlana": {
            "stone_id": "11111111-1111-4111-8111-111111111111",
            "name": "Svetlana",
            "stone_type": "MARBLE",
            "adoption_status": "AVAILABLE",
        },
        "Madame Obsidian": {
            "stone_id": "22222222-2222-4222-8222-222222222222",
            "name": "Madame Obsidian",
            "stone_type": "OBSIDIAN",
            "adoption_status": "AVAILABLE",
        },
    }

    @tool
    async def lookup(name: str) -> list[dict[str, Any]]:
        """Read exact PostgreSQL name matches."""
        return [names[name]]

    request = ReferenceRequest(
        stone_name="Svetlana",
        recommendation_name="Madame Obsidian",
        care_types=[],
        pairs=[],
        pair_lists=[],
    )
    result = await read_reference(
        ToolPlan(tools=["get_stone_status_by_name"], reason="Resolve each named identity"),
        request,
        ReferenceTools(
            stone_status=lookup,
            stone_details=lookup,
            timeline=lookup,
            encyclopedia=lookup,
            exact_pair=lookup,
            pair_list=lookup,
        ),
        {},
        include_status=False,
    )
    assert result.stone is not None and result.stone.name == "Svetlana"
    assert result.recommendation_stone is not None
    assert result.recommendation_stone.name == "Madame Obsidian"
    assert result.recommendation_issue is None
    assert len(result.sources) == 2
