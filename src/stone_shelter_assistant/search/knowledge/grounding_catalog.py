"""An editable Typesense concept/example catalog, loaded as a complete versioned pack."""

import hashlib
import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool
from typesense import AsyncClient

from stone_shelter_assistant.search.enums import AccommodationFactType
from stone_shelter_assistant.search.infrastructure.typesense_collections import (
    GROUNDING_COLLECTION,
    ensure_grounding_collection,
)
from stone_shelter_assistant.stones.enums import StoneType


class GroundingEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str = Field(min_length=1)
    language: str = Field(pattern=r"^[A-Za-z0-9-]+$")
    catalog_version: str = Field(pattern=r"^[A-Za-z0-9._-]+$")
    concept_id: str = Field(min_length=1)
    entry_kind: Literal["definition", "example"]
    text: str = Field(min_length=1)
    expected: Literal["supported", "contradicted", "unknown"] | None = None
    proposed_value: StrictBool | None = None
    proposed_type: StoneType | None = None
    applies_to_pair: tuple[StoneType, StoneType] | None = None


class GroundingSnapshot(BaseModel):
    language: str
    catalog_version: str
    content_hash: str
    entries: list[GroundingEntry]


def build_grounding_snapshot(
    entries: list[GroundingEntry], language: str, version: str
) -> GroundingSnapshot:
    if not entries or len({e.id for e in entries}) != len(entries):
        raise ValueError("Grounding catalog must contain unique entries")
    if any(e.language != language or e.catalog_version != version for e in entries):
        raise ValueError("Catalog language/version mismatch")
    concepts = {
        "candidate_type",
        "candidate_compatibility",
        "candidate_environment_fit",
        *(kind.value for kind in AccommodationFactType),
    }
    definitions = [e.concept_id for e in entries if e.entry_kind == "definition"]
    if set(definitions) != concepts or len(definitions) != len(concepts):
        raise ValueError("Catalog must define each supported concept exactly once")
    if any(
        e.concept_id not in concepts or (e.entry_kind == "example" and e.expected is None)
        for e in entries
    ):
        raise ValueError("Unknown concept or unlabeled example")
    ordered = sorted(entries, key=lambda e: e.id)
    payload = json.dumps(
        [e.model_dump(mode="json") for e in ordered], sort_keys=True, ensure_ascii=False
    )
    return GroundingSnapshot(
        language=language,
        catalog_version=version,
        content_hash="sha256:" + hashlib.sha256(payload.encode()).hexdigest(),
        entries=ordered,
    )


class GroundingCatalog:
    def __init__(self, client: AsyncClient, *, language: str, version: str) -> None:
        self.client = client
        self.language = language
        self.version = version

    async def load(self) -> GroundingSnapshot:
        """Fetch all entries by exact language/version, never relevance top-k."""
        entries: list[GroundingEntry] = []
        page = 1
        while True:
            result = await self.client.collections[GROUNDING_COLLECTION].documents.search(
                {
                    "q": "*",
                    "query_by": "text",
                    "filter_by": f"language:=`{self.language}` && catalog_version:=`{self.version}`",
                    "per_page": 100,
                    "page": page,
                }
            )
            entries.extend(
                GroundingEntry.model_validate(hit["document"]) for hit in result.get("hits", [])
            )
            found = result["found"]
            if len(entries) >= found:
                break
            if not result.get("hits"):
                raise ValueError("Incomplete grounding catalog page")
            page += 1
        if len(entries) != found:
            raise ValueError("Catalog changed during loading")
        return build_grounding_snapshot(entries, self.language, self.version)

    async def search(self, query: str) -> list[GroundingEntry]:
        result = await self.client.collections[GROUNDING_COLLECTION].documents.search(
            {
                "q": query,
                "query_by": "text,concept_id",
                "per_page": 100,
                "filter_by": f"language:=`{self.language}` && catalog_version:=`{self.version}`",
            }
        )
        return [GroundingEntry.model_validate(hit["document"]) for hit in result.get("hits", [])]

    async def upsert(self, entry: GroundingEntry) -> GroundingSnapshot:
        current = await self.load()
        entries = [old for old in current.entries if old.id != entry.id] + [entry]
        snapshot = build_grounding_snapshot(entries, self.language, self.version)
        await self.client.collections[GROUNDING_COLLECTION].documents.upsert(
            entry.model_dump(mode="json", exclude_none=True)
        )
        return snapshot

    async def reload(self, seed: Path) -> GroundingSnapshot:
        entries = [GroundingEntry.model_validate(e) for e in json.loads(seed.read_text())]
        snapshot = build_grounding_snapshot(entries, self.language, self.version)
        await ensure_grounding_collection(self.client)
        documents = self.client.collections[GROUNDING_COLLECTION].documents
        await documents.delete(
            {"filter_by": f"language:=`{self.language}` && catalog_version:=`{self.version}`"}
        )
        for entry in snapshot.entries:
            await documents.upsert(entry.model_dump(mode="json", exclude_none=True))
        return snapshot
