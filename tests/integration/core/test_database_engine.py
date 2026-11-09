import pytest
from sqlalchemy import text

from stone_shelter_assistant.core.database_factories import (
    create_database_engine,
    create_session_factory,
)
from stone_shelter_assistant.core.settings import DatabaseSettings


@pytest.mark.asyncio
async def test_application_db_engine(
    migrated_database: DatabaseSettings,
) -> None:
    engine = create_database_engine(migrated_database)
    try:
        async with engine.connect() as connection:
            result = await connection.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_create_session_factory(
    migrated_database: DatabaseSettings,
) -> None:
    engine = create_database_engine(migrated_database)
    session_factory = create_session_factory(engine)
    try:
        async with session_factory() as session:
            result = await session.execute(text("SELECT 1"))
            assert result.scalar_one() == 1
    finally:
        await engine.dispose()
