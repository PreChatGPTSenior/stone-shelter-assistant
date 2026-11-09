"""Dependency wiring for use cases. Later create a session per execution and bind the Unit of Work and participating module adapters to that same session. Keep business decisions in use cases."""

from collections.abc import AsyncIterator

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from stone_shelter.application.register_stone import RegisterStoneService
from stone_shelter.catalog.persistence.repository import (
    SqlAlchemyShelterCaseRepository,
    SqlAlchemyStoneRepository,
)
from stone_shelter.infrastructure.database.unit_of_work import SqlAlchemyUnitOfWork
from stone_shelter.search.qdrant_index import QdrantStoneIndexer
from stone_shelter.search.typesense_index import TypesenseStoneIndexer


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


async def get_typesense_stone_indexer(
    request: Request,
) -> AsyncIterator[TypesenseStoneIndexer]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield TypesenseStoneIndexer(
            stone_repository=SqlAlchemyStoneRepository(session),
            shelter_case_repository=SqlAlchemyShelterCaseRepository(session),
            typesense_client=request.app.state.typesense_client,
        )


async def get_qdrant_stone_indexer(
    request: Request,
) -> AsyncIterator[QdrantStoneIndexer]:
    session_factory: async_sessionmaker[AsyncSession] = request.app.state.session_factory

    async with session_factory() as session:
        yield QdrantStoneIndexer(
            stone_repository=SqlAlchemyStoneRepository(session),
            shelter_case_repository=SqlAlchemyShelterCaseRepository(session),
            qdrant_client=request.app.state.qdrant_client,
            embeddings=request.app.state.embeddings,
            embedding_dimension=request.app.state.embedding_dimension,
        )
