# Local development setup

Run all commands from the repository root. The application uses persistent local PostgreSQL; automated database tests use disposable Testcontainers databases. The registration endpoint accepts one stone with its case, history, and optional profile, and returns HTTP 201 with only the generated internal UUID. See ADR-0014 for the database-target policy.

## Prerequisites

- uv available on your PATH.
- Python 3.13, which uv can provision when synchronizing the project.
- Docker with the daemon running for integration tests. Docker Compose is used for the development application, not for test database startup.
- Make for the combined development check command.

## Install dependencies

```sh
uv sync --locked
```

This creates or updates the project-local `.venv` and installs the locked application and development dependencies. Run project commands through `uv run` to use this environment.

## Configure the local environment

This section configures the development application and manual Alembic commands. Integration tests use explicit Testcontainers settings and do not require this `.env` file.

If `.env` does not already exist, copy the template:

```sh
cp .env.example .env
```

Keep an existing `.env` rather than overwriting it. Replace the password placeholders with local values before the first infrastructure startup. Do not commit `.env` or credentials.

The application consumes these PostgreSQL settings:

| Variable | Purpose | Local template value |
| --- | --- | --- |
| `POSTGRES_HOST` | Host reachable by the application | `127.0.0.1` |
| `POSTGRES_PORT` | Published PostgreSQL port | `55432` |
| `POSTGRES_DB` | Database name | `stone_shelter_py` |
| `POSTGRES_USER` | Database user | `stone_shelter_py` |
| `POSTGRES_PASSWORD` | Database password | Set locally; no credential is documented here |

`DatabaseSettings` reads `.env` relative to the working directory. Existing environment variables take precedence over values in `.env`. The same PostgreSQL values configure Docker Compose and the application.

The template also contains Redis, MinIO, and Ollama settings for later features. They are not required by the current database implementation. PostgreSQL settings are already wired into the application.

## Start PostgreSQL

```sh
docker compose up -d --wait postgres
docker compose ps postgres
```

This Compose service is for the development application. Integration tests start their own PostgreSQL container and do not require the Compose PostgreSQL service. Redis, MinIO, and Ollama are not required for the current tests or application bootstrap. Additional infrastructure details are in [infra/README.md](../infra/README.md).

The application runs on the host and connects through the published port. PostgreSQL data is stored in the Compose project's named volume.

To stop PostgreSQL while retaining its data:

```sh
docker compose stop postgres
```

## Local Typesense infrastructure

The Compose configuration includes the official Typesense 30.2 image pinned to its multi-platform digest. It publishes the HTTP API on 127.0.0.1:58108 by default and keeps index data in the separate typesense-data named volume. This prepares the local lexical-search service; the async Python client is configured during FastAPI lifespan. Collections, indexing, and search operations are not implemented yet.

Set TYPESENSE_API_KEY in the local .env to a private development key and optionally change TYPESENSE_PORT (default 58108). Preserve existing PostgreSQL and storage settings. The key is passed to the server through its environment; never commit the local .env. The .env.example value is a placeholder, not a shared credential.

Start only Typesense and check readiness from the host:

```sh
docker compose up -d typesense
docker compose ps typesense
curl --fail --show-error http://127.0.0.1:58108/health
```

Use the configured host port if TYPESENSE_PORT was changed. The health endpoint should return {"ok":true}. This is a manual readiness check; the Compose service does not define an in-container healthcheck. No extra healthcheck tools are installed into the official image.

Stop it while retaining index data:

```sh
docker compose stop typesense
```

The Python application runs on the host. TypesenseSettings reads TYPESENSE_HOST, TYPESENSE_PORT, TYPESENSE_API_KEY, optional TYPESENSE_PROTOCOL (http by default), and optional TYPESENSE_CONNECTION_TIMEOUT_SECONDS (10 by default). The local host is 127.0.0.1. The official typesense 2.1.1 AsyncClient uses these validated settings with automatic retries disabled. Lifespan creates app.state.typesense_client and closes its HTTP pool on shutdown; it does not issue a readiness request or create collections at startup. No browser integration or CORS setting is needed for that path. Automated search-engine tests must use separate disposable infrastructure, not this persistent index. The connection integration is checked against disposable Testcontainers, not the persistent development index. The session-scoped Typesense container has a random host port and its own explicit key; TypesenseSettings disables dotenv loading in tests. Async client fixtures are function-scoped to match the pytest-asyncio event loop and close their HTTP pools after use. The authenticated SDK smoke test reads /debug and checks the pinned server version. Ordinary tests perform no model/provider calls.

Official references: [installation](https://typesense.org/docs/guide/install-typesense.html) and [server configuration](https://typesense.org/docs/30.2/api/server-configuration.html).

Typesense connection verification on 2026-11-05: `make check` passed (43 tests; mypy checked 82 source files). The SDK emits an AnalyticsV1 deprecation warning while constructing its client; this application does not call that API, and the warning is not suppressed.

## Local Qdrant infrastructure

Compose also provides Qdrant on `127.0.0.1:${QDRANT_PORT:-56333}` with a separate persistent `qdrant-data` volume. Set `QDRANT_PORT` in the local `.env` only if the default host port conflicts. Start it with `docker compose up -d qdrant`; check readiness with `curl --fail --show-error http://127.0.0.1:56333/readyz`. This is service preparation only: Python settings, client ownership, collections, vector indexing and automated Qdrant tests are planned in PY-016.

## Manage migrations

The manual commands in this section target the database selected by development configuration. Test migrations are applied automatically to the disposable Testcontainers database instead.

Apply all available revisions:

```sh
uv run alembic upgrade head
uv run alembic current
```

Inspect revision files and their history:

```sh
uv run alembic heads
uv run alembic history
```

`heads` describes the available revision graph; `current` reports the revision applied to the configured database. Alembic stores the applied revision in `alembic_version`.

Do not run rollback experiments or test cleanup against this persistent database. Migration generation and schema verification use clean Testcontainers databases with explicit connection settings. Review generated revisions before applying them locally. If an existing local schema or data conflicts with a migration, stop and inspect the problem; do not delete the volume or reset data automatically.

Review generated upgrade and downgrade operations before applying them. Alembic uses `Base.metadata`, populated by the model imports in `infrastructure/database/models.py`. Catalog tables use the `stone_shelter` schema; the migration version table remains in `public`. Migration execution is a separate CLI operation and does not run automatically at application startup. The current environment supports database-connected commands; offline SQL generation with `--sql` is not implemented.

## Run the application

```sh
uv run uvicorn stone_shelter.main:app --reload --host 127.0.0.1 --port 8000
```

Open [Swagger UI](http://127.0.0.1:8000/docs) or the [OpenAPI document](http://127.0.0.1:8000/openapi.json).

The application lifespan creates the engine and stores the session factory on application state. Shutdown disposes the engine. Creating the engine does not itself establish a database connection or perform a readiness check. Each Unit of Work creates its own session when entered; writes require an explicit commit.

Stop the server with `Ctrl+C`.

## Prepare reference shelters and load authored stones

After applying migrations, create the two reference shelters once (the command can safely be repeated when the existing records match):

```sh
uv run python -m stone_shelter.tools.seed_shelters
```

This reads `fixtures/shelters.json` and uses the database configured in `.env`. It creates missing shelters and leaves matching existing records unchanged. Conflicting existing records cause an error and roll back that setup transaction. This command does not create stones.

With the application running in another terminal, submit the ten authored requests:

```sh
uv run python -m stone_shelter.tools.load_stones
```

Override the application URL or request directory when needed:

```sh
uv run python -m stone_shelter.tools.load_stones --base-url http://127.0.0.1:8000 --directory fixtures/stones
```

Each request must include the source-owned current `shelterCase.adoptionStatus`; the application stores it without calculating status from history.

The loader sends every JSON file verbatim to `POST /api/v1/stones`, one request and transaction per stone. It reports each created ID or failure and a final summary; exit code 0 means all files succeeded, while 1 means at least one failed or no files were found. It does not connect to PostgreSQL, perform server-side DTO validation locally, retry, or delete data. A timeout can leave the server outcome unknown.

Successful registrations remain in the local database across application and PostgreSQL restarts. Replaying the same external IDs is not supported as an update or automatic skip; uniqueness constraints reject duplicates, and a dedicated duplicate-response contract is still deferred. Submit only new files on subsequent runs. Do not point the loader at `tests/fixtures/stone-registration/invalid-*` for normal application filling.

Stop the application with Ctrl+C and PostgreSQL with `docker compose stop postgres`; start it again with `docker compose up -d --wait postgres`. Do not use volume deletion to stop the environment.

## Run checks and tests

Run the full local development check sequence with one command:

```sh
make check
```

This runs Ruff autofix, Ruff formatting, mypy, and pytest, in that order, stopping at the first failing command. Ruff intentionally updates source files. Docker must be available; a development PostgreSQL instance and local `.env` are not required by the integration fixtures. There is no separate development-database `alembic check` command in this target: the migration fixture runs `upgrade head` and then `check` against the fresh container database. `check` detects pending autogenerated schema operations; `upgrade head` applies the migrations.

Read-only lint, formatting, and type checks:

```sh
uv run ruff check --no-fix .
uv run ruff format --check .
uv run mypy
```

`--no-fix` overrides the project's default Ruff autofix setting. Mypy checks application code, tests, and migration scripts.

Run unit tests without PostgreSQL or Docker; they do not request the integration container fixtures:

```sh
uv run pytest tests/unit
```

Run PostgreSQL integration tests, or the complete suite, with the Docker daemon available:

```sh
uv run pytest tests/integration
uv run pytest
```

### Integration database lifecycle

Shared fixtures live in `tests/integration/conftest.py`:

1. `postgres_container` starts one new PostgreSQL/pgvector container per pytest session when first requested, using the same pinned image as development. Docker assigns a host port dynamically. No development volumes are attached.
2. `database_settings` supplies all connection fields explicitly from the container and disables dotenv loading. Tests do not use the development port or credentials.
3. `migrated_database` invokes Alembic through the pytest interpreter in a child process. The child receives container-only PostgreSQL settings and runs from a temporary directory without the development `.env`. It applies the complete migration chain and checks schema drift before database-backed tests run.
4. The shared `app` fixture substitutes those settings into the application lifespan. HTTP requests and independent verification sessions use the same disposable database.
5. Each test releases its own async engines/sessions and cleans up its records or technical tables. Session teardown stops and removes the test container. Downloaded Docker images may remain cached.

The schema starts empty for each pytest session, not each individual test. Existing per-test cleanup is therefore still required. Container startup or migration errors fail setup; there is no fallback to development PostgreSQL and no silent skip when Docker is unavailable. The existing OpenAPI-only test does not require a database connection.

Focused lifecycle and transaction tests:

```sh
uv run pytest tests/unit/application/test_lifespan.py
uv run pytest tests/unit/application/test_unit_of_work.py
uv run pytest tests/integration/test_database_engine.py
uv run pytest tests/integration/test_unit_of_work.py
uv run pytest tests/integration/catalog/test_register_stone.py -v
```

Transaction integration tests create uniquely named technical tables in the disposable container database and remove them during fixture cleanup. Business tables are created by migrations, not `create_all()`. The tests cover explicit commit, uncommitted exit, and exception rollback. Registration rollback tests additionally verify atomicity across stones, profiles, cases, and events.

Registration tests send file-based requests through FastAPI and verify the complete persisted graph using a new session. They cover ten valid histories and nine rejected input scenarios; separate service tests verify full rollback for missing shelter references and duplicate event UUIDs. The loader is also exercised through the same HTTP application against Testcontainers. See [registration scenarios](testing/registration-scenarios.md).

### PY-007 verification evidence

On 2026-10-29, the full suite passed: **24 tests**. Runtime inspection observed a single PostgreSQL target, `localhost:51548/stone_shelter_test`, distinct from the development port `55432`. A temporary in-memory connection guard rejected non-test targets during that verification; it is not a permanent repository feature. The container was removed afterwards. Alembic upgrade and check passed, and mypy passed for 63 source files.

After formatting cleanup, the owner reported that the complete `make check` target passed. The owner then chose to complete PY-007 without further verification runs. A separate run with `.env` absent and development PostgreSQL stopped was not performed and is not claimed as verified. Unit tests separately passed (12 tests) with `DOCKER_HOST` pointing to a nonexistent socket. Fixed example ports in this evidence describe that run only; future test-container ports are dynamic.
