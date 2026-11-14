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

`POST /api/v1/stones/reload` replaces local operational fixture records and their search collections. Use it only when intentionally resetting the learning dataset; starting the API does not seed it automatically.

```sh
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/stones/reload
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/encyclopedia/reindex
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/compatibility/reindex
curl --fail-with-body -X POST http://127.0.0.1:8000/api/v1/knowledge/grounding/reload
```

Each reference reload replaces its own indexed source; catalog reload replaces the selected language/version from the authored seed. The active pack is English `en-v1`.

## Ask a question

This endpoint calls the configured models and records a Langfuse trace:

```sh
# Reuse one session ID to group questions from the same run in Langfuse.
curl --fail-with-body -H 'X-Session-ID: STPY-manual-questions-001' \
  --json '{"question":"Is Madame Obsidian available and compatible with granite?"}' \
  http://127.0.0.1:8000/api/v1/questions
```

## Local checks

```sh
uv run ruff check --no-fix .
uv run mypy
uv run pytest
```

Integration tests use disposable Testcontainers and controlled embeddings, not persistent local data. Live model tests are skipped unless explicitly enabled. Scenario inputs and evaluation rubrics are under [agent-eval fixtures](../tests/fixtures/agent-eval).

### Frozen candidate-assessment replay

The current opt-in runner is [test_candidate_assessment.py](../tests/live/test_candidate_assessment.py). It requires `RUN_OPENROUTER_EVALUATION=1`; inspect its settings and the case input before a paid run.

### Full questions flow with DeepEval

The opt-in runner is [test_questions_model_evaluation.py](../tests/integration/test_questions_model_evaluation.py), also gated by `RUN_OPENROUTER_EVALUATION=1`. The [twenty-case suite](../tests/fixtures/agent-eval/questions-challenge-20/README.md) documents its separate gate and scenario contract.

For repeated comparisons, reuse `EVALUATION_COMPARISON_ID` and assign a new `EVALUATION_RUN_NUMBER` to each configuration execution. The six-model runner numbers selected configurations consecutively from that number. Without an explicit comparison ID, each invocation starts a new comparison; the default run number is 1.

```sh
export EVALUATION_COMPARISON_ID=challenge20-model-study
export EVALUATION_RUN_NUMBER=1
```

These variables only label a run; model calls still require explicit authorization and the runner's opt-in flag. Each run uses session `STPY-<comparison_id>-r<run_number>` with at least two digits for the number. API comparison requests must send that session in `X-Session-ID` and both `comparison_id` and `run_number` in the JSON body. Find the run in Langfuse by session or comparison metadata; use each archived case's `trace_id` to inspect a single question. The API returns a `configuration_id` derived from the effective application model settings; judge settings are recorded separately by the evaluation runner.

Evaluation datasets use `STPY-<suite-name>` (for example `STPY-quiet-home-questions-v4` and `STPY-quiet-home-candidate-assessment`). Dataset item IDs include the dataset name, case and input hash. Datasets identify fixed inputs; sessions identify executions. New run outputs are saved separately under the suite's `runs/` directory.
