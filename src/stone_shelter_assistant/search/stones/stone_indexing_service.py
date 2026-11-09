"""Read a registered stone once and project it into both search indexes."""

from uuid import UUID

from stone_shelter_assistant.search.document_models import (
    CaseEventSearchDocument,
    StoneSearchDocument,
)
from stone_shelter_assistant.search.stones.qdrant_indexer import QdrantStoneIndexer
from stone_shelter_assistant.search.stones.stone_document_builder import (
    build_case_event_document,
    build_stone_document,
)
from stone_shelter_assistant.search.stones.typesense_indexer import TypesenseStoneIndexer
from stone_shelter_assistant.stones.repository_protocols import (
    ShelterCaseRepository,
    StoneRepository,
)


class StoneIndexingService:
    def __init__(
        self,
        stone_repository: StoneRepository,
        shelter_case_repository: ShelterCaseRepository,
        typesense_indexer: TypesenseStoneIndexer,
        qdrant_indexer: QdrantStoneIndexer,
    ) -> None:
        self._stone_repository = stone_repository
        self._shelter_case_repository = shelter_case_repository
        self._typesense_indexer = typesense_indexer
        self._qdrant_indexer = qdrant_indexer

    async def index(self, stone_id: UUID) -> None:
        stone = await self._stone_repository.get_by_id(stone_id)
        if stone is None:
            raise LookupError(f"Stone {stone_id} was not found")

        case = await self._shelter_case_repository.get_by_stone_id(stone_id)
        if case is None:
            raise LookupError(f"Case for stone {stone_id} was not found")

        documents: list[StoneSearchDocument | CaseEventSearchDocument] = [
            build_stone_document(stone, case, stone.profile),
            *(build_case_event_document(stone, case, event) for event in case.events),
        ]
        for document in documents:
            await self._typesense_indexer.index(document)
            await self._qdrant_indexer.index(document)
