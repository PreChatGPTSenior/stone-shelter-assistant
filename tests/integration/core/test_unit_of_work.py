from collections.abc import AsyncIterator
from uuid import uuid4

import pytest
import pytest_asyncio
from sqlalchemy import Column, Integer, MetaData, Table, select
from sqlalchemy.ext.asyncio import AsyncEngine

from stone_shelter_assistant.core.database_factories import (
    create_database_engine,
    create_session_factory,
)
from stone_shelter_assistant.core.settings import DatabaseSettings
from stone_shelter_assistant.core.unit_of_work import SqlAlchemyUnitOfWork


@pytest_asyncio.fixture
async def database_table(
    migrated_database: DatabaseSettings,
) -> AsyncIterator[tuple[AsyncEngine, Table]]:
    engine = create_database_engine(migrated_database)
    metadata = MetaData()
    table = Table(
        f"uow_test_{uuid4().hex}",
        metadata,
        Column("id", Integer, primary_key=True),
    )

    try:
        async with engine.begin() as connection:
            await connection.run_sync(metadata.create_all)

        yield engine, table
    finally:
        try:
            async with engine.begin() as connection:
                await connection.run_sync(metadata.drop_all)
        finally:
            await engine.dispose()


@pytest.mark.asyncio
async def test_unit_of_work_commit_persists_data(
    database_table: tuple[AsyncEngine, Table],
) -> None:
    engine, table = database_table
    session_factory = create_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    async with uow:
        await uow.session.execute(table.insert().values(id=1))
        await uow.commit()

    async with session_factory() as verification_session:
        result = await verification_session.execute(select(table.c.id))
        assert result.scalars().all() == [1]


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_without_commit(
    database_table: tuple[AsyncEngine, Table],
) -> None:
    engine, table = database_table
    session_factory = create_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    async with uow:
        await uow.session.execute(table.insert().values(id=1))

        result = await uow.session.execute(select(table.c.id))
        assert result.scalars().all() == [1]

    async with session_factory() as verification_session:
        result = await verification_session.execute(select(table.c.id))
        assert result.scalars().all() == []


@pytest.mark.asyncio
async def test_unit_of_work_rolls_back_on_exception(
    database_table: tuple[AsyncEngine, Table],
) -> None:
    engine, table = database_table
    session_factory = create_session_factory(engine)
    uow = SqlAlchemyUnitOfWork(session_factory)

    with pytest.raises(ValueError, match="Registration failed"):
        async with uow:
            await uow.session.execute(table.insert().values(id=1))

            raise ValueError("Registration failed")

    async with session_factory() as verification_session:
        result = await verification_session.execute(select(table.c.id))
        assert result.scalars().all() == []
