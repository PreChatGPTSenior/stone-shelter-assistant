from uuid import UUID

from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models

from stone_shelter.catalog.application.ports import ShelterCaseRepository, StoneRepository
from stone_shelter.search.prepare import build_stone_document, embedding_text
from stone_shelter.search.qdrant_schema import OPERATIONAL_COLLECTION


class QdrantStoneIndexer:
    def __init__(
        self,
        stone_repository: StoneRepository,
        shelter_case_repository: ShelterCaseRepository,
        qdrant_client: AsyncQdrantClient,
        embeddings: Embeddings,
        embedding_dimension: int,
    ) -> None:
        self._stone_repository = stone_repository
        self._shelter_case_repository = shelter_case_repository
        self._qdrant_client = qdrant_client
        self._embeddings = embeddings
        self._embedding_dimension = embedding_dimension

    async def index(self, stone_id: UUID) -> None:
        stone = await self._stone_repository.get_by_id(stone_id)
        if stone is None:
            raise LookupError(f"Stone {stone_id} was not found")

        case = await self._shelter_case_repository.get_by_stone_id(stone_id)
        if case is None:
            raise LookupError(f"Case for stone {stone_id} was not found")

        document = build_stone_document(stone, case)
        vector = (await self._embeddings.aembed_documents([embedding_text(document)]))[0]

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
