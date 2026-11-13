# Local setup

Requires uv, Docker, Python 3.13 and a local Ollama instance with `qwen3-embedding:0.6b`. Run commands from the repository root.

## Start

```sh
uv sync --locked
# Only when .env does not exist:
cp .env.example .env
```

Configure the local database/search credentials, Ollama, OpenRouter and Langfuse using the template. Keep `.env` private. The API runs on the host; Docker provides PostgreSQL, Typesense and Qdrant.

```sh
docker compose up -d --wait postgres typesense qdrant
uv run alembic upgrade head
uv run uvicorn stone_shelter_assistant.app:create_app --factory --reload
```

API documentation: `http://127.0.0.1:8000/docs`.

## Load the learning fixtures

`normalize-data` replaces local operational fixture records and their search collections. Use it only when intentionally resetting the learning dataset; starting the API does not seed it automatically.

```sh
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/testing/normalize-data
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/encyclopedia/reindex
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/compatibility/reindex
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/grounding/reload
```

Each reference reload replaces its own indexed source; catalog reload replaces the selected language/version from the authored seed. The active pack is English `en-v1`.

## Ask a question

This endpoint calls the configured models and records a Langfuse trace:

```sh
curl --fail-with-body --json '{"question":"Is Madame Obsidian available and compatible with granite?"}' \
  http://127.0.0.1:8000/api/v1/questions
```

## Local checks

```sh
uv run ruff check --no-fix .
uv run mypy
uv run pytest
```

Integration tests use disposable Testcontainers and controlled embeddings, not persistent local data. Live model tests are skipped unless explicitly enabled. Scenario inputs and frozen results are under [agent-eval fixtures](../tests/fixtures/agent-eval).

### Frozen candidate-assessment replay

The current opt-in runner is [test_candidate_assessment.py](../tests/live/test_candidate_assessment.py). It requires `RUN_OPENROUTER_EVALUATION=1`; inspect its settings and the case input before a paid run.

### Full questions flow with DeepEval

The opt-in runner is [test_questions_model_evaluation.py](../tests/integration/test_questions_model_evaluation.py), also gated by `RUN_OPENROUTER_EVALUATION=1`. The [twenty-case suite](../tests/fixtures/agent-eval/questions-challenge-20/README.md) documents its separate gate and frozen records. Historical runs retain their original settings and contracts.
