from unittest.mock import AsyncMock, Mock

import pytest
from fastapi.testclient import TestClient
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncEngine
from typesense import AsyncClient

from stone_shelter_assistant.app import create_app


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

    qdrant_settings = Mock()
    qdrant_settings_class = Mock(return_value=qdrant_settings)
    qdrant_client = AsyncMock(spec=AsyncQdrantClient)
    qdrant_creator = Mock(return_value=qdrant_client)
    ensure_qdrant_collection = AsyncMock()

    embedding_settings = Mock(embedding_dimension=8)
    embedding_settings_class = Mock(return_value=embedding_settings)
    embeddings = Mock()
    embeddings_creator = Mock(return_value=embeddings)

    monkeypatch.setattr(
        "stone_shelter_assistant.app.DatabaseSettings",
        settings_class,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.create_database_engine",
        engine_creator,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.create_session_factory",
        factory_creator,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.TypesenseSettings",
        typesense_settings_class,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.create_typesense_client",
        typesense_creator,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.ensure_typesense_operational_collection",
        ensure_collection,
    )
    monkeypatch.setattr("stone_shelter_assistant.app.QdrantSettings", qdrant_settings_class)
    monkeypatch.setattr("stone_shelter_assistant.app.create_qdrant_client", qdrant_creator)
    monkeypatch.setattr(
        "stone_shelter_assistant.app.ensure_qdrant_operational_collection",
        ensure_qdrant_collection,
    )
    monkeypatch.setattr(
        "stone_shelter_assistant.app.OllamaEmbeddingSettings", embedding_settings_class
    )
    monkeypatch.setattr("stone_shelter_assistant.app.create_embeddings", embeddings_creator)

    app = create_app()

    with TestClient(app):
        settings_class.assert_called_once_with()
        engine_creator.assert_called_once_with(settings)
        factory_creator.assert_called_once_with(engine)

        typesense_settings_class.assert_called_once_with()
        typesense_creator.assert_called_once_with(typesense_settings)
        ensure_collection.assert_awaited_once_with(typesense_client)
        qdrant_settings_class.assert_called_once_with()
        qdrant_creator.assert_called_once_with(qdrant_settings)
        embedding_settings_class.assert_called_once_with()
        embeddings_creator.assert_called_once_with(embedding_settings)
        ensure_qdrant_collection.assert_awaited_once_with(qdrant_client, vector_size=8)

        assert app.state.session_factory is session_factory
        assert app.state.typesense_client is typesense_client
        assert app.state.qdrant_client is qdrant_client
        assert app.state.embeddings is embeddings
        assert app.state.embedding_dimension == 8
        qdrant_client.close.assert_not_awaited()
        typesense_client.api_call.aclose.assert_not_awaited()
        engine.dispose.assert_not_awaited()

    engine.dispose.assert_awaited_once_with()
    typesense_client.api_call.aclose.assert_awaited_once_with()
    qdrant_client.close.assert_awaited_once_with()
