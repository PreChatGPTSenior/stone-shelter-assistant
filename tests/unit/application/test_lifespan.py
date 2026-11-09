from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncEngine
from typesense import AsyncClient

from stone_shelter.bootstrap.app import create_app


def test_lifespan_initializes_and_disposes_shared_resources(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = Mock()
    settings_class = Mock(return_value=settings)

    engine = AsyncMock(spec=AsyncEngine)
    engine_creator = Mock(return_value=engine)

    session_factory = Mock()
    factory_creator = Mock(return_value=session_factory)

    typesense_settings = Mock()
    typesense_settings_class = Mock(return_value=typesense_settings)
    typesense_client = Mock(spec=AsyncClient)
    typesense_client.api_call = Mock()
    typesense_client.api_call.aclose = AsyncMock()
    typesense_creator = Mock(return_value=typesense_client)

    ensure_collection = AsyncMock()

    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.DatabaseSettings",
        settings_class,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.create_database_engine",
        engine_creator,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.create_session_factory",
        factory_creator,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.TypesenseSettings",
        typesense_settings_class,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.create_typesense_client",
        typesense_creator,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.ensure_typesense_operational_collection",
        ensure_collection,
    )

    app = create_app()

    with TestClient(app):
        settings_class.assert_called_once_with()
        engine_creator.assert_called_once_with(settings)
        factory_creator.assert_called_once_with(engine)

        typesense_settings_class.assert_called_once_with()
        typesense_creator.assert_called_once_with(typesense_settings)
        ensure_collection.assert_awaited_once_with(typesense_client)

        assert app.state.session_factory is session_factory
        assert app.state.typesense_client is typesense_client
        typesense_client.api_call.aclose.assert_not_awaited()
        engine.dispose.assert_not_awaited()

    engine.dispose.assert_awaited_once_with()
    typesense_client.api_call.aclose.assert_awaited_once_with()
