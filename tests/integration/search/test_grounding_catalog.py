"""Exercise the editable catalog in disposable Typesense only."""

import json
from pathlib import Path

import httpx
import pytest
from fastapi import FastAPI

from stone_shelter_assistant.search.knowledge.grounding_catalog import (
    GroundingCatalog,
)


@pytest.mark.asyncio
async def test_catalog_reload_search_edit_and_complete_version_read(app: FastAPI) -> None:
    seed = Path(__file__).parents[3] / "fixtures/knowledge/grounding/grounding_en-v1.json"
    expected_ids = {entry["id"] for entry in json.loads(seed.read_text())}
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as http:
        response = await http.post("/api/v1/knowledge/grounding/reload")
        assert response.status_code == 200, response.text
        assert response.json()["count"] == len(expected_ids)
        old_hash = response.json()["content_hash"]
        found = await http.get("/api/v1/knowledge/grounding/search", params={"q": "rotate"})
        assert found.status_code == 200 and found.json()
        entry = next(e for e in found.json() if e["id"] == "en-v1-example-rotation-asserted")
        scoped = next(
            e for e in found.json() if e["id"] == "en-v1-example-rotation-other-pair-not-denial"
        )
        assert scoped["applies_to_pair"] == ["PUMICE", "PUMICE"]
        entry["text"] = "We agreed to rotate shared decisions. Catalogeditmarker."
        changed = await http.put("/api/v1/knowledge/grounding/entries/" + entry["id"], json=entry)
        assert changed.status_code == 200, changed.text
        assert changed.json()["content_hash"] != old_hash
        found = await http.get(
            "/api/v1/knowledge/grounding/search", params={"q": "Catalogeditmarker"}
        )
        assert [e["id"] for e in found.json()] == [entry["id"]]
    catalog = GroundingCatalog(app.state.typesense_client, language="en", version="en-v1")
    snapshot = await catalog.load()
    assert {entry.id for entry in snapshot.entries} == expected_ids
    scoped_entry = next(
        e for e in snapshot.entries if e.id == "en-v1-example-rotation-other-pair-not-denial"
    )
    assert scoped_entry.applies_to_pair == ("PUMICE", "PUMICE")
    assert any(e.text.endswith("Catalogeditmarker.") for e in snapshot.entries)
    # Definitions and examples are a separate catalog, not operational stone documents.
    assert (await app.state.typesense_client.collections["grounding_catalog"].retrieve())[
        "num_documents"
    ] == len(expected_ids)
