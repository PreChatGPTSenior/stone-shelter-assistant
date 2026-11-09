from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models

from stone_shelter_assistant.search.document_content import build_embedding_text
from stone_shelter_assistant.search.document_models import (
    CaseEventSearchDocument,
    StoneSearchDocument,
)
from stone_shelter_assistant.search.infrastructure.qdrant_collections import OPERATIONAL_COLLECTION


class QdrantStoneIndexer:
    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embeddings: Embeddings,
        embedding_dimension: int,
    ) -> None:
        self._qdrant_client = qdrant_client
        self._embeddings = embeddings
        self._embedding_dimension = embedding_dimension

    async def index(self, document: StoneSearchDocument | CaseEventSearchDocument) -> None:
        text = build_embedding_text(document.title, document.text)
        vector = (await self._embeddings.aembed_documents([text]))[0]

        if len(vector) != self._embedding_dimension:
            raise ValueError("Embedding dimension does not match Qdrant collection")

        await self._qdrant_client.upsert(
            collection_name=OPERATIONAL_COLLECTION,
            points=[
                models.PointStruct(
                    id=str(document.id),
                    vector=vector,
                    payload=document.model_dump(
                        mode="json",
                        exclude={"id"},
                    ),
                )
            ],
            wait=True,
        )
