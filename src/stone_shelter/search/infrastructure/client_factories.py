"""Construct search service clients and local embedding adapters."""

from langchain_ollama import OllamaEmbeddings
from qdrant_client import AsyncQdrantClient
from typesense import AsyncClient

from stone_shelter.core.settings import (
    OllamaEmbeddingSettings,
    QdrantSettings,
    TypesenseSettings,
)


def create_embeddings(settings: OllamaEmbeddingSettings) -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.embedding_model,
        base_url=settings.base_url,
    )


def create_qdrant_client(settings: QdrantSettings) -> AsyncQdrantClient:
    return AsyncQdrantClient(host=settings.host, port=settings.port)


def create_typesense_client(settings: TypesenseSettings) -> AsyncClient:
    """Create a client whose lifecycle is owned by the caller.

    Args:
        settings: Validated Typesense connection settings.

    Returns:
        An asynchronous client configured without automatic request retries.
    """
    return AsyncClient(
        {
            "nodes": [
                {
                    "host": settings.host,
                    "port": settings.port,
                    "protocol": settings.protocol,
                }
            ],
            "api_key": settings.api_key.get_secret_value(),
            "connection_timeout_seconds": settings.connection_timeout_seconds,
            "num_retries": 0,
        }
    )
