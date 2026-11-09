from typesense import AsyncClient

from stone_shelter_assistant.search.document_models import (
    CaseEventSearchDocument,
    StoneSearchDocument,
)
from stone_shelter_assistant.search.infrastructure.typesense_collections import (
    OPERATIONAL_COLLECTION,
)


class TypesenseStoneIndexer:
    def __init__(
        self,
        typesense_client: AsyncClient,
    ) -> None:
        self._typesense_client = typesense_client

    async def index(self, document: StoneSearchDocument | CaseEventSearchDocument) -> None:
        await self._typesense_client.collections[OPERATIONAL_COLLECTION].documents.upsert(
            document.model_dump(mode="json")
        )
