"""HTTP routes for fixture preparation and the manual search baseline."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from langchain_core.tools import BaseTool

from stone_shelter_assistant.assistant.api_contracts import QuestionRequest
from stone_shelter_assistant.dependencies import get_manual_search_tools, get_stone_fixture_loader
from stone_shelter_assistant.stones.fixture_loader import StoneFixtureLoader

router = APIRouter(prefix="/api/v1/testing", tags=["manual-testing"])


@router.post("/normalize-data")
async def normalize_data(
    loader: Annotated[StoneFixtureLoader, Depends(get_stone_fixture_loader)],
) -> dict[str, int]:
    """Replace the development shelter and stone records and their search projections."""
    return await loader.reload()


@router.post("/manual-test")
async def manual_test(
    payload: QuestionRequest,
    tools: Annotated[dict[str, BaseTool], Depends(get_manual_search_tools)],
) -> dict[str, object]:
    """Run the Madame Obsidian and granite baseline with the real search tools."""
    name = "Madame Obsidian"
    if name.casefold() not in payload.question.casefold():
        raise HTTPException(
            status_code=422, detail=f"The manual baseline expects a question about {name}."
        )

    hits = await tools["search_stones_lexical"].ainvoke({"query": name})
    card = next((hit for hit in hits if hit["title"] == name), None)
    if card is None:
        raise HTTPException(status_code=404, detail=f"{name} was not found in Typesense.")

    details = await tools["get_stone_details"].ainvoke({"stone_id": card["id"]})
    if details is None or details["shelter_case"] is None:
        raise HTTPException(
            status_code=404, detail=f"{name} or her case was not found in PostgreSQL."
        )

    pair = await tools["get_compatibility_pair"].ainvoke(
        {"first_type": details["stone_type"], "second_type": "GRANITE"}
    )
    if pair is None:
        raise HTTPException(status_code=404, detail="The granite compatibility rule was not found.")
    return {
        "question": payload.question,
        "search_hit": card,
        "stone_details": details,
        "compatibility_rule": pair,
    }
