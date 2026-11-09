from uuid import uuid4

import httpx
import pytest
from fastapi import FastAPI
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_pair_key,
)
from stone_shelter_assistant.stones.enums import StoneType


@pytest.mark.asyncio
async def test_knowledge_endpoints_replace_only_the_requested_source(app: FastAPI) -> None:
    typesense_client: AsyncClient = app.state.typesense_client
    qdrant: AsyncQdrantClient = app.state.qdrant_client

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for source, count in (("encyclopedia", 14), ("compatibility", 66)):
            response = await client.post(f"/api/v1/knowledge/{source}/reindex")
            assert response.status_code == 200, response.text
            assert response.json() == {f"indexed_{source}_documents": count}

    collection = typesense_client.collections["knowledge"]
    assert (await collection.retrieve())["num_documents"] == 80
    assert (await qdrant.count("knowledge", exact=True)).count == 80

    encyclopedia = await collection.documents.search(
        {
            "q": "Obsidian",
            "query_by": "title",
            "filter_by": "document_kind:=encyclopedia_section && stone_types:=OBSIDIAN",
        }
    )
    assert encyclopedia["found"] == 1
    assert encyclopedia["hits"][0]["document"]["section_path"] == ["Obsidian"]

    pair_key = build_pair_key(StoneType.BASALT, StoneType.BASALT)
    pairs = await collection.documents.search(
        {
            "q": "*",
            "query_by": "title",
            "filter_by": (
                f"document_kind:=compatibility_pair && pair_key:=`{pair_key}`"
                " && verdict:=CONDITIONAL"
            ),
        }
    )
    assert pairs["found"] == 1
    pair = pairs["hits"][0]["document"]
    assert pair["stone_types"] == ["BASALT", "BASALT"]

    points, _ = await qdrant.scroll(
        collection_name="knowledge",
        scroll_filter=models.Filter(
            must=[
                models.FieldCondition(key="pair_key", match=models.MatchValue(value=pair_key)),
                models.FieldCondition(key="verdict", match=models.MatchValue(value="CONDITIONAL")),
            ],
        ),
        with_vectors=True,
    )
    assert [point.id for point in points] == [pair["id"]]
    assert points[0].payload == {key: value for key, value in pair.items() if key != "id"}
    assert isinstance(points[0].vector, list) and len(points[0].vector) == 8

    # Obsolete IDs survive an upsert, so they distinguish replacement from a regular import.
    for original in (encyclopedia["hits"][0]["document"], pair):
        stale_id = str(uuid4())
        stale = {**original, "id": stale_id}
        await collection.documents.upsert(stale)
        await qdrant.upsert(
            "knowledge",
            points=[
                models.PointStruct(
                    id=stale_id,
                    vector=points[0].vector,
                    payload={key: value for key, value in stale.items() if key != "id"},
                )
            ],
            wait=True,
        )

    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://test"
    ) as client:
        for source, remaining in (("encyclopedia", 81), ("compatibility", 80)):
            response = await client.post(f"/api/v1/knowledge/{source}/reindex")
            assert response.status_code == 200, response.text
            assert (await collection.retrieve())["num_documents"] == remaining
            assert (await qdrant.count("knowledge", exact=True)).count == remaining
