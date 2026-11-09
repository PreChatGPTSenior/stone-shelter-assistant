"""Replace each authored reference source in both search engines."""

from collections.abc import Sequence
from pathlib import Path
from typing import Final

from langchain_core.embeddings import Embeddings
from qdrant_client import AsyncQdrantClient, models
from typesense import AsyncClient

from stone_shelter_assistant.search.document_content import build_embedding_text
from stone_shelter_assistant.search.document_models import KnowledgeSearchDocument
from stone_shelter_assistant.search.enums import DocumentKind
from stone_shelter_assistant.search.infrastructure import qdrant_collections, typesense_collections
from stone_shelter_assistant.search.knowledge.encyclopedia_document_builder import (
    build_encyclopedia_documents,
)
from stone_shelter_assistant.search.knowledge.stone_compatibility_document_builder import (
    build_stone_compatibility_documents,
)

ENCYCLOPEDIA_PATH: Final = Path("fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md")
COMPATIBILITY_PATH: Final = Path(
    "fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json"
)


class KnowledgeIndexer:
    def __init__(
        self,
        project_root: Path,
        typesense: AsyncClient,
        qdrant: AsyncQdrantClient,
        embeddings: Embeddings,
        embedding_dimension: int,
    ) -> None:
        self._project_root = project_root
        self._typesense = typesense
        self._qdrant = qdrant
        self._embeddings = embeddings
        self._embedding_dimension = embedding_dimension

    async def reload_encyclopedia(self) -> int:
        documents = build_encyclopedia_documents(
            (self._project_root / ENCYCLOPEDIA_PATH).read_text(encoding="utf-8"),
            ENCYCLOPEDIA_PATH.as_posix(),
        )
        return await self._replace(documents, (DocumentKind.ENCYCLOPEDIA_SECTION,))

    async def reload_compatibility(self) -> int:
        documents = build_stone_compatibility_documents(
            (self._project_root / COMPATIBILITY_PATH).read_text(encoding="utf-8"),
            COMPATIBILITY_PATH.as_posix(),
        )
        return await self._replace(
            documents,
            (
                DocumentKind.COMPATIBILITY_PAIR,
                DocumentKind.COMPATIBILITY_TYPE_PORTRAIT,
                DocumentKind.COMPATIBILITY_READING_RULES,
            ),
        )

    async def _replace(
        self,
        documents: Sequence[KnowledgeSearchDocument],
        kinds: tuple[DocumentKind, ...],
    ) -> int:
        vectors = await self._embeddings.aembed_documents(
            [build_embedding_text(doc.title, doc.text) for doc in documents]
        )
        points = [
            models.PointStruct(
                id=str(doc.id),
                vector=vector,
                payload=doc.model_dump(mode="json", exclude={"id"}),
            )
            for doc, vector in zip(documents, vectors, strict=True)
        ]

        await typesense_collections.ensure_knowledge_collection(self._typesense)
        await qdrant_collections.ensure_knowledge_collection(
            self._qdrant, vector_size=self._embedding_dimension
        )
        typesense_documents = self._typesense.collections[
            typesense_collections.KNOWLEDGE_COLLECTION
        ].documents
        await typesense_documents.delete({"filter_by": f"document_kind:=[{','.join(kinds)}]"})
        await self._qdrant.delete(
            collection_name=qdrant_collections.KNOWLEDGE_COLLECTION,
            points_selector=models.FilterSelector(
                filter=models.Filter(
                    must=[
                        models.FieldCondition(
                            key="document_kind",
                            match=models.MatchAny(any=[kind.value for kind in kinds]),
                        )
                    ]
                )
            ),
            wait=True,
        )

        results = await typesense_documents.import_(
            [doc.model_dump(mode="json") for doc in documents], {"action": "upsert"}
        )
        for document, result in zip(documents, results, strict=True):
            if not result["success"]:
                raise RuntimeError(
                    f"Typesense rejected {document.source_key}: {result.get('error')}"
                )

        await self._qdrant.upsert(
            collection_name=qdrant_collections.KNOWLEDGE_COLLECTION,
            points=points,
            wait=True,
        )
        return len(documents)
