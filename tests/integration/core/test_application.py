import httpx
import pytest

from stone_shelter.app import create_app


@pytest.mark.asyncio
async def test_application_serves_openapi() -> None:
    app = create_app()

    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/openapi.json")

    assert response.status_code == 200
    assert response.json()["info"]["title"] == "Stone Shelter API"
