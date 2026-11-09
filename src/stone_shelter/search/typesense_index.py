from uuid import UUID

from typesense import AsyncClient

from stone_shelter.catalog.application.ports import ShelterCaseRepository, StoneRepository
from stone_shelter.search.prepare import build_stone_document
from stone_shelter.search.typesense_schema import OPERATIONAL_COLLECTION


class TypesenseStoneIndexer:
    def __init__(
        self,
        stone_repository: StoneRepository,
        shelter_case_repository: ShelterCaseRepository,
        typesense_client: AsyncClient,
    ) -> None:

        self._stone_repository = stone_repository
        self._shelter_case_repository = shelter_case_repository
        self._typesense_client = typesense_client

    async def index(self, stone_id: UUID) -> None:
        stone = await self._stone_repository.get_by_id(stone_id)
        if stone is None:
            raise LookupError(f"Stone {stone_id} was not found")
        case = await self._shelter_case_repository.get_by_stone_id(stone_id)
        if case is None:
            raise LookupError(f"Case for stone {stone_id} was not found")

        document = build_stone_document(stone, case)
        await self._typesense_client.collections[OPERATIONAL_COLLECTION].documents.upsert(
            document.model_dump(mode="json")
        )
