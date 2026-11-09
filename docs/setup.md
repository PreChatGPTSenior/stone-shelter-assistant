# Local setup

Run commands from the repository root. The application uses persistent local services; integration tests use disposable Testcontainers and never use the local PostgreSQL database.

## Requirements

- uv and Docker with a running daemon; Python 3.13 can be installed by uv.
- A local Ollama instance with `qwen3-embedding:0.6b` for real vector indexing. Automated tests substitute controlled embeddings.

## Install and configure

```sh
uv sync --locked
cp .env.example .env
```

Copy the template only if `.env` does not exist. Set private local passwords and the Typesense API key. The application runs on the host, so use these values in `.env`:

```dotenv
POSTGRES_HOST=127.0.0.1
TYPESENSE_HOST=127.0.0.1
QDRANT_HOST=127.0.0.1
OLLAMA_BASE_URL=http://127.0.0.1:11434
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:0.6b
OLLAMA_EMBEDDING_DIMENSION=1024
```

Keep the port values from `.env.example` unless changed locally. Do not commit `.env`.

## Start the local application

```sh
docker compose up -d --wait postgres typesense qdrant
uv run alembic upgrade head
ollama list
uv run uvicorn stone_shelter.main:app --reload
```

The first three services keep data in Docker named volumes. `ollama list` should show the configured embedding model; Ollama runs separately from Compose. The API documentation is available at `http://127.0.0.1:8000/docs`. The local database is not seeded by setup; registration requires existing shelter records. The authored JSON fixtures remain available for isolated integration tests.

## Checks

```sh
uv run ruff check --no-fix .
uv run ruff format --check .
uv run mypy
uv run pytest
```

Integration tests start temporary PostgreSQL, Typesense, and Qdrant containers and replace Ollama embeddings with known vectors. Docker is required, but the local `.env` and persistent services are not used by those tests. `make check` is also available; it applies Ruff fixes and formatting before running mypy and pytest, so it can edit files.
