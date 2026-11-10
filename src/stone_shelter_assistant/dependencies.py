"""Wire request-scoped services and indexers to database sessions."""

from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated

from fastapi import Depends, Request
from langchain_core.tools import BaseTool
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stone_shelter_assistant.assistant.tools import (
    knowledge_search_tools,
    stone_lookup_tools,
    stone_search_tools,
)
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter_assistant.search.knowledge.knowledge_indexer import KnowledgeIndexer
from stone_shelter_assistant.search.knowledge.knowledge_search_service import KnowledgeSearchService
from stone_shelter_assistant.search.stones.qdrant_indexer import QdrantStoneIndexer
from stone_shelter_assistant.search.stones.stone_indexing_service import StoneIndexingService
from stone_shelter_assistant.search.stones.stone_search_service import StoneSearchService
from stone_shelter_assistant.search.stones.typesense_indexer import TypesenseStoneIndexer
from stone_shelter_assistant.stones.fixture_loader import StoneFixtureLoader
from stone_shelter_assistant.stones.repository import (
    SqlAlchemyShelterCaseRepository,
    SqlAlchemyStoneRepository,
)
from stone_shelter_assistant.stones.service import RegisterStoneService, StoneIngestionService


async def get_register_stone_service(
    request: Request,
) -> AsyncIterator[RegisterStoneService]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    uow = SqlAlchemyUnitOfWork(session_factory)

    async with uow:
        repository = SqlAlchemyStoneRepository(uow.session)
        service = RegisterStoneService(
            repository=repository,
            uow=uow,
        )

        yield service


async def get_stone_indexing_service(
    request: Request,
) -> AsyncIterator[StoneIndexingService]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield StoneIndexingService(
            stone_repository=SqlAlchemyStoneRepository(session),
            shelter_case_repository=SqlAlchemyShelterCaseRepository(session),
            typesense_indexer=TypesenseStoneIndexer(
                typesense_client=request.app.state.typesense_client,
            ),
            qdrant_indexer=QdrantStoneIndexer(
                qdrant_client=request.app.state.qdrant_client,
                embeddings=request.app.state.embeddings,
                embedding_dimension=request.app.state.embedding_dimension,
            ),
        )


def get_stone_ingestion_service(
    registration: Annotated[RegisterStoneService, Depends(get_register_stone_service)],
    indexer: Annotated[StoneIndexingService, Depends(get_stone_indexing_service)],
) -> StoneIngestionService:
    return StoneIngestionService(registration, indexer)


def get_stone_fixture_loader(
    request: Request,
    ingestion: Annotated[StoneIngestionService, Depends(get_stone_ingestion_service)],
) -> StoneFixtureLoader:
    resources = request.app.state
    return StoneFixtureLoader(
        project_root=Path.cwd(),
        sessions=resources.session_factory,
        typesense=resources.typesense_client,
        qdrant=resources.qdrant_client,
        embedding_dimension=resources.embedding_dimension,
        ingestion=ingestion,
    )


async def get_manual_search_tools(request: Request) -> AsyncIterator[dict[str, BaseTool]]:
    resources = request.app.state
    sessions: async_sessionmaker[AsyncSession] = resources.session_factory
    stone_search = StoneSearchService(
        resources.typesense_client, resources.qdrant_client, resources.embeddings
    )
    knowledge_search = KnowledgeSearchService(
        resources.typesense_client, resources.qdrant_client, resources.embeddings
    )
    async with sessions() as session:
        yield {
            tool.name: tool
            for tool in (
                *stone_search_tools(stone_search, SqlAlchemyShelterCaseRepository(session)),
                *stone_lookup_tools(SqlAlchemyStoneRepository(session)),
                *knowledge_search_tools(knowledge_search),
            )
        }


def get_knowledge_indexer(request: Request) -> KnowledgeIndexer:
    return KnowledgeIndexer(
        project_root=Path.cwd(),
        typesense=request.app.state.typesense_client,
        qdrant=request.app.state.qdrant_client,
        embeddings=request.app.state.embeddings,
        embedding_dimension=request.app.state.embedding_dimension,
    )
