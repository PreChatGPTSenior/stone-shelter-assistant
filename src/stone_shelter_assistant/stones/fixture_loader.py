"""Replace operational data with the local project fixtures."""

from pathlib import Path
from uuid import UUID

from pydantic import TypeAdapter
from qdrant_client import AsyncQdrantClient
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from typesense import AsyncClient

from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.stones.api_contracts import StoneRegistrationRequest
from stone_shelter_assistant.stones.models import (
    CaseEventModel,
    ShelterCaseModel,
    ShelterModel,
    StoneModel,
    StoneProfileModel,
)
from stone_shelter_assistant.stones.service import StoneIngestionService


class StoneFixtureLoader:
    def __init__(
        self,
        project_root: Path,
        sessions: async_sessionmaker[AsyncSession],
        typesense: AsyncClient,
        qdrant: AsyncQdrantClient,
        embedding_dimension: int,
        ingestion: StoneIngestionService,
    ) -> None:
        self._project_root = project_root
        self._sessions = sessions
        self._typesense = typesense
        self._qdrant = qdrant
        self._embedding_dimension = embedding_dimension
        self._ingestion = ingestion

    async def reload(self) -> dict[str, int]:
        """Replace shelters, stones, cases, profiles, events, and their projections."""
        fixtures = self._project_root / "fixtures"
        shelter_rows = TypeAdapter(list[dict[str, str]]).validate_json(
            (fixtures / "shelters.json").read_bytes()
        )
        shelters = [
            ShelterModel(id=UUID(row["id"]), name=row["name"], address=row["address"])
            for row in shelter_rows
        ]
        stones = [
            StoneRegistrationRequest.model_validate_json(path.read_bytes())
            for path in sorted((fixtures / "stones").glob("*.json"))
        ]
        typesense_names = {row["name"] for row in await self._typesense.collections.retrieve()}
        qdrant_names = {row.name for row in (await self._qdrant.get_collections()).collections}

        async with self._sessions.begin() as session:
            for model in (
                CaseEventModel,
                StoneProfileModel,
                ShelterCaseModel,
                StoneModel,
                ShelterModel,
            ):
                await session.execute(delete(model))
            session.add_all(shelters)

        typesense_name = typesense_collections.OPERATIONAL_COLLECTION
        if typesense_name in typesense_names:
            await self._typesense.collections[typesense_name].delete()
        qdrant_name = qdrant_collections.OPERATIONAL_COLLECTION
        if qdrant_name in qdrant_names and not await self._qdrant.delete_collection(qdrant_name):
            raise RuntimeError(f"Qdrant could not delete collection {qdrant_name}")

        await typesense_collections.ensure_operational_collection(self._typesense)
        await qdrant_collections.ensure_operational_collection(
            self._qdrant, vector_size=self._embedding_dimension
        )
        for stone in stones:
            await self._ingestion.ingest(stone)

        return {"shelters": len(shelters), "stones": len(stones)}
