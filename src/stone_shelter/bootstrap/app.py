"""Application composition and lifecycle. Assemble FastAPI, register routers and error handlers, and manage shared resource startup and shutdown."""

from collections.abc import AsyncIterator
from contextlib import AsyncExitStack, asynccontextmanager

from fastapi import FastAPI

from stone_shelter.catalog.api.router import router as catalog_router
from stone_shelter.infrastructure.database.engine import create_database_engine
from stone_shelter.infrastructure.database.session import create_session_factory
from stone_shelter.infrastructure.embeddings import create_embeddings
from stone_shelter.infrastructure.qdrant import create_qdrant_client
from stone_shelter.infrastructure.typesense import create_typesense_client
from stone_shelter.search.qdrant_schema import (
    ensure_operational_collection as ensure_qdrant_operational_collection,
)
from stone_shelter.search.typesense_schema import (
    ensure_operational_collection as ensure_typesense_operational_collection,
)
from stone_shelter.settings import (
    DatabaseSettings,
    OllamaEmbeddingSettings,
    QdrantSettings,
    TypesenseSettings,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with AsyncExitStack() as resources:
        engine = create_database_engine(DatabaseSettings())
        resources.push_async_callback(engine.dispose)

        typesense_client = create_typesense_client(TypesenseSettings())
        resources.push_async_callback(typesense_client.api_call.aclose)

        await ensure_typesense_operational_collection(typesense_client)

        app.state.session_factory = create_session_factory(engine)
        app.state.typesense_client = typesense_client

        qdrant_client = create_qdrant_client(QdrantSettings())
        resources.push_async_callback(qdrant_client.close)
        app.state.qdrant_client = qdrant_client

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
        title="Stone Shelter API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.include_router(catalog_router)

    return app
