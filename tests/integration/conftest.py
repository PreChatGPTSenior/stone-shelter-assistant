"""Shared fixtures for disposable PostgreSQL and Typesense integration tests."""

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
import pytest_asyncio
from fastapi import FastAPI
from pydantic import SecretStr
from testcontainers.community.postgres import PostgresContainer
from testcontainers.core.container import DockerContainer
from testcontainers.core.wait_strategies import HttpWaitStrategy
from typesense import AsyncClient

from stone_shelter.infrastructure.typesense import create_typesense_client
from stone_shelter.settings import DatabaseSettings, TypesenseSettings

POSTGRES_IMAGE = (
    "pgvector/pgvector:0.8.6-pg18-trixie"
    "@sha256:78bf48b801e792f99e3ac62b5036fd3876e9be48afda16c1e331af1c75ceb2ff"
)

TYPESENSE_IMAGE = (
    "typesense/typesense:30.2"
    "@sha256:610f2d34b1f93d00762869da2c67736775e5798d19a2c8b91b014b8a0cc1e110"
)

# Used only by disposable integration-test containers.
TYPESENSE_TEST_API_KEY = "integration-test-typesense-key"


@pytest.fixture(scope="session")
def postgres_container() -> Iterator[PostgresContainer]:
    with PostgresContainer(
        image=POSTGRES_IMAGE,
        username="integration_test",
        password="integration_test",
        dbname="stone_shelter_test",
        driver=None,
    ) as postgres:
        yield postgres


@pytest.fixture(scope="session")
def typesense_container() -> Iterator[DockerContainer]:
    """Provide a disposable Typesense instance for integration tests."""
    wait_strategy = (
        HttpWaitStrategy(8108, "/health")
        .for_status_code(200)
        .for_response_predicate(lambda body: json.loads(body).get("ok") is True)
        .with_startup_timeout(60)
    )

    container = (
        DockerContainer(TYPESENSE_IMAGE)
        .with_env("TYPESENSE_API_KEY", TYPESENSE_TEST_API_KEY)
        .with_exposed_ports(8108)
        .with_command(["--data-dir=/tmp"])
        .waiting_for(wait_strategy)
    )

    with container as typesense:
        yield typesense


@pytest.fixture(scope="session")
def typesense_settings(
    typesense_container: DockerContainer,
) -> TypesenseSettings:
    """Use only the disposable container, never local development settings."""
    return TypesenseSettings(
        _env_file=None,
        host=typesense_container.get_container_host_ip(),
        port=int(typesense_container.get_exposed_port(8108)),
        protocol="http",
        api_key=SecretStr(TYPESENSE_TEST_API_KEY),
        connection_timeout_seconds=10.0,
    )


@pytest_asyncio.fixture
async def typesense_client(
    typesense_settings: TypesenseSettings,
) -> AsyncIterator[AsyncClient]:
    """Keep each asynchronous client within its test's event loop."""
    client = create_typesense_client(typesense_settings)
    try:
        yield client
    finally:
        await client.api_call.aclose()


@pytest.fixture(scope="session")
def database_settings(
    postgres_container: PostgresContainer,
) -> DatabaseSettings:
    return DatabaseSettings(
        _env_file=None,
        host=postgres_container.get_container_host_ip(),
        port=int(postgres_container.get_exposed_port(5432)),
        db=postgres_container.dbname,
        user=postgres_container.username,
        password=SecretStr(postgres_container.password),
    )


@pytest.fixture(scope="session")
def migrated_database(
    database_settings: DatabaseSettings,
) -> DatabaseSettings:
    project_root = Path(__file__).resolve().parents[2]

    environment = os.environ.copy()
    environment.update(
        {
            "POSTGRES_HOST": database_settings.host,
            "POSTGRES_PORT": str(database_settings.port),
            "POSTGRES_DB": database_settings.db,
            "POSTGRES_USER": database_settings.user,
            "POSTGRES_PASSWORD": (database_settings.password.get_secret_value()),
        }
    )

    with TemporaryDirectory(prefix="stone-shelter-migrations-") as working_directory:
        for arguments in (("upgrade", "head"), ("check",)):
            subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "alembic",
                    "-c",
                    str(project_root / "alembic.ini"),
                    *arguments,
                ],
                cwd=working_directory,
                env=environment,
                check=True,
            )

    return database_settings


@pytest_asyncio.fixture
async def app(
    migrated_database: DatabaseSettings,
    typesense_settings: TypesenseSettings,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[FastAPI]:
    # Service integration tests do not depend on the HTTP application imports.
    from stone_shelter.bootstrap.app import create_app

    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.DatabaseSettings",
        lambda: migrated_database,
    )
    monkeypatch.setattr(
        "stone_shelter.bootstrap.app.TypesenseSettings",
        lambda: typesense_settings,
    )

    application = create_app()

    async with application.router.lifespan_context(application):
        yield application
