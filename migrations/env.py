"""Run async Alembic migrations against the registered ORM metadata."""

import asyncio

from alembic import context
from sqlalchemy.engine import Connection

from stone_shelter_assistant.core.base_models import Base
from stone_shelter_assistant.core.database_factories import create_database_engine
from stone_shelter_assistant.core.settings import DatabaseSettings
from stone_shelter_assistant.stones import models as stone_models  # noqa: F401


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=Base.metadata,
        version_table_schema="public",
        include_schemas=True,
        include_name=lambda name, type_, parent_names: (
            type_ != "schema" or name == "stone_shelter_assistant"
        ),
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    engine = create_database_engine(DatabaseSettings())

    try:
        async with engine.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await engine.dispose()


asyncio.run(run_async_migrations())
