"""Assemble FastAPI routers and manage shared resource lifecycles."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from stone_shelter_assistant.assistant.router import router as assistant_router
from stone_shelter_assistant.core.database_factories import (
    create_database_engine,
    create_session_factory,
)
from stone_shelter_assistant.core.settings import (
    DatabaseSettings,
    OllamaEmbeddingSettings,
    QdrantSettings,
    TypesenseSettings,
)
from stone_shelter_assistant.search.infrastructure.client_factories import (
    create_embeddings,
    create_qdrant_client,
    create_typesense_client,
)
from stone_shelter_assistant.search.infrastructure.qdrant_collections import (
    ensure_operational_collection as ensure_qdrant_operational_collection,
)
from stone_shelter_assistant.search.infrastructure.typesense_collections import (
    ensure_operational_collection as ensure_typesense_operational_collection,
)
from stone_shelter_assistant.search.knowledge.router import router as knowledge_router
from stone_shelter_assistant.stones.router import router as stones_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as resources:
        #postgres
        engine = create_database_engine(DatabaseSettings())
        resources.push_async_callback(engine.dispose)
        app.state.session_factory = create_session_factory(engine)
        #typesense
        typesense_client = create_typesense_client(TypesenseSettings())
        resources.push_async_callback(typesense_client.api_call.aclose)
        await ensure_typesense_operational_collection(typesense_client)
        app.state.typesense_client = typesense_client
        #qdrant
        qdrant_client = create_qdrant_client(QdrantSettings())
        resources.push_async_callback(qdrant_client.close)
        app.state.qdrant_client = qdrant_client
        #embedding
        embedding_settings = OllamaEmbeddingSettings()
        embeddings = create_embeddings(embedding_settings)
        app.state.embeddings = embeddings
        app.state.embedding_dimension = embedding_settings.embedding_dimension

        await ensure_qdrant_operational_collection(
            qdrant_client, vector_size=embedding_settings.embedding_dimension
        )

        yield


def create_app() -> FastAPI:
    """Build and configure the HTTP application."""
    app = FastAPI(
        title="Stone Shelter Assistant API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(stones_router)
    app.include_router(knowledge_router)
    app.include_router(assistant_router)

    return app
