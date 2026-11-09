from qdrant_client import AsyncQdrantClient

from stone_shelter.settings import QdrantSettings


def create_qdrant_client(settings: QdrantSettings) -> AsyncQdrantClient:
    return AsyncQdrantClient(host=settings.host, port=settings.port)
