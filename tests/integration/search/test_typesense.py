import pytest
from typesense import AsyncClient


@pytest.mark.asyncio
async def test_typesense_client_authenticates_against_container(
    typesense_client: AsyncClient,
) -> None:
    """Exercise an authenticated SDK request against the pinned server image."""
    response = await typesense_client.debug.retrieve()

    assert response["version"] == "30.2"
