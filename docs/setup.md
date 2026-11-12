# Local setup

The repository and checkout directory are named `stone-shelter-assistant`. The Python package is `stone_shelter_assistant`.

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

Use `COMPOSE_PROJECT_NAME=stone-shelter-assistant` and the `stone_shelter_assistant` SQL schema. The PostgreSQL user is `stone_shelter_assistant_app`, keeping the default schema independent of the application schema. The renamed learning project starts with fresh local storage.

## Start the local application

```sh
docker compose up -d --wait postgres typesense qdrant
uv run alembic upgrade head
ollama list
uv run uvicorn stone_shelter_assistant.app:create_app --factory --reload
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

With the API, Typesense, Qdrant, and the configured Ollama embedding model running, reload each reference source explicitly:

```sh
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/encyclopedia/reindex
curl -X POST http://127.0.0.1:8000/api/v1/knowledge/compatibility/reindex
```

Each endpoint deletes and reloads its own source in the shared `knowledge` collection in both engines.

## Local HTTP baseline

Run the two knowledge reloads above, then replace the local stone and shelter fixtures.
The reset deletes the current operational records and both `stones` search collections before
repopulating them. Use it as a maintenance operation in the local development environment.

```sh
curl --fail-with-body -X POST \
  http://127.0.0.1:8000/api/v1/testing/normalize-data

curl --fail-with-body \
  --json '{"question":"Is Madame Obsidian available and compatible with granite?"}' \
  http://127.0.0.1:8000/api/v1/testing/manual-test
```

The second endpoint reads the prepared data and returns the three tool results.
Send the same question JSON to `POST /api/v1/questions` to run LangGraph with OpenRouter and get a Langfuse `trace_id`. Set `OPENROUTER_API_KEY`, `LANGFUSE_PUBLIC_KEY`, and `LANGFUSE_SECRET_KEY` in `.env`. Set `LANGFUSE_BASE_URL` if your Langfuse project uses a host other than `https://cloud.langfuse.com`.

For the evaluation and answer stages, model selection uses the first configured value in this order:

1. The stage request field `evaluation_model_id` or `answer_model_id`.
2. The shared request field `model_id`.
3. The stage default `OPENROUTER_EVALUATION_MODEL` or `OPENROUTER_ANSWER_MODEL`.
4. The default `dots-studio/dots-3-note-preview:free` for evaluation. The answer stage falls back to `OPENROUTER_MODEL`, which defaults to `openrouter/free`.

The response and Langfuse trace input include the effective stage selections in `model_ids`. The response field `model_id` still reports the shared fallback. The evaluation model runs when character or compatibility evidence needs interpretation.

The shortlist stage uses `selection_model_id`, then the shared request `model_id`, then `OPENROUTER_SELECTION_MODEL`, then `OPENROUTER_MODEL`. The question parser uses `parsing_model_id`, then the shared request `model_id`, then `OPENROUTER_PARSING_MODEL`, then the resolved shortlist model. The planner uses `planning_model_id`, then the shared request `model_id`, then `OPENROUTER_PLANNING_MODEL`, then the resolved parser model.

Parsing, semantic grounding and planning run first. Status, care, and compatibility use the validated reference plan. The parser proposes English lexical/semantic queries and a candidate type referenced to the question. The separate grounding model verifies sensitive proposals against the selected catalog, then code builds AVAILABLE/en filters; traits remain assessment criteria. Langfuse records parser_diagnostics for discarded proposals. General recommendations execute one hybrid Typesense/Qdrant operation (two backend calls); named recommendations use lexical lookup (one call). There is no search-agent LLM stage or agent_model_id field. Each model stage makes at most one call. Langfuse records per-engine inputs, fusion contributions, selection decisions and verified outcomes under one trace_id. The plan and its reason are recorded in Langfuse.

During stabilization, active questions, fixture content/names, prompts and tests use English only. Historical experiment records retain their original language. Absent parser collections/groups default to empty collections; null lists and malformed nonempty references remain invalid. Svetlana's current fixture and indexed name are English.

Named information uses requested_stone_info with overview, preferences or care. The plan resolves the exact PostgreSQL name, reads get_stone_details, and uses that card's type for knowledge. An overview reads the authoritative case timeline, encyclopedia, compatibility portrait and all verdict groups; preferences use individual facts only. collect_reference_evidence uses the configured evaluation model (Luna in the current experiment configuration), checks exact source/quote binding and assigns scope in code. The answer model composes separate individual/history/encyclopedia/compatibility sections with validated source IDs. Failed composition exposes checked quotations or explicitly labeled original sources. Citation validity does not establish semantic entailment. Unsupported material-care requests preserve their quoted material name and report missing authored knowledge instead of substituting another type. For shortlisted candidates the graph also reads PostgreSQL observation events when character or compatibility is assessed. Evidence keeps a literal observation source label plus an event UUID and preserves the parent stone/case, date, type and exact notes. Profile/preferences outrank observations, which outrank biography and general encyclopedia; conflicts remain visible. Used observation sources survive in excluded-candidate answers. Event dates do not prove when a behavior began, and event-only candidate discovery before the shortlist is not implemented. Recommendation answers render every checked household pair, including harmonious ones, with general guide text and condition status. No same-household multi-type interaction beyond pairwise rules is inferred.

To try strict shortlist output, set `selection_model_id` to `nvidia/nemotron-3.5-super-vl:free` or `dots-studio/dots-3-note-preview:free`. The shortlist stage uses strict JSON Schema for the model IDs in `OPENROUTER_SELECTION_JSON_SCHEMA_MODELS` (a JSON array) and function calling for the rest. Langfuse records the chosen output method and how many duplicate criteria were removed. The response includes `candidate_decisions` with the checked adoption status and graph disposition for each card.

Evidence assessment uses strict JSON Schema for the models in `OPENROUTER_EVALUATION_JSON_SCHEMA_MODELS` (a JSON array) and function calling for other models. Its Langfuse output records `assessment_output_method` when the stage calls a model.

For an evaluation run, send `eval_case_id` and `fixture_version` in the request. Reuse those values when comparing the same question and data on different models. Each request still gets a distinct trace ID.

### Frozen candidate-assessment replay

The [agent-evaluation fixture archive](../tests/fixtures/agent-eval/quiet-home-with-granite/README.md) stores the fixed input, reviewed expectations, and six-model comparison results together. It also documents token accounting and the Dots provider-error retry. The active replay fixture is maintained against the current application contract; archived inputs are reference records only.

The opt-in test in `tests/live/test_candidate_assessment.py` evaluates the current-contract fixture in `tests/fixtures/assistant/quiet-home-assessment.json`. It uses the application's structured-output wrapper and candidate scoring with recorded cards, statuses, criteria, and evidence. The fixture contains the current prompt, explicit source records and CandidateEvidence schema and requires no database or search services. It is not a reproduction of a historical model request.

Run the six-model experiment explicitly. It makes paid OpenRouter calls and records comparable runs in the Langfuse dataset `PY-037/quiet-home-candidate-assessment`.

```bash
RUN_OPENROUTER_EVALUATION=1 uv run pytest -q -s tests/live/test_candidate_assessment.py
```

Set `OPENROUTER_EVALUATION_MODEL` to one of the model IDs in the test to replay only that model. All calls allow 8192 output tokens. DeepSeek requests high reasoning, and the other five models request medium. Each model is checked for a valid DTO, exact source references and quotes, character coverage, and unsupported compatibility conditions. Failed model checks deliberately fail the test. Ordinary test runs skip the experiment.

### Full questions flow with DeepEval

The `eval` dependency group includes DeepEval. The opt-in integration test rebuilds authored fixtures in disposable Testcontainers, calls `POST /api/v1/questions`, reads the recorded parser and assessment outputs from Langfuse, and scores them with deterministic checks and G-Eval. Knowledge retrieval in this test is lexical. Stone-card semantic retrieval uses real Ollama embeddings. Unused knowledge vectors and case-event vectors are excluded from the live experiment setup.

```bash
RUN_OPENROUTER_EVALUATION=1 DEEPEVAL_TELEMETRY_OPT_OUT=YES uv run --group eval pytest -q -s tests/integration/test_questions_model_evaluation.py
```

The test accepts a single model or comma-separated IDs in `OPENROUTER_EVALUATION_MODEL`. Normal stage settings select the upstream models. Set `OPENROUTER_EVALUATION_QUESTION` and `OPENROUTER_EVALUATION_CASE_ID` for a separate question variant. `OPENROUTER_EXPECT_CONDITION_PAIR=GRANITE+GRANITE` additionally requires both authored condition IDs to appear with status `unknown`.

The questions request supports `evaluation_max_tokens` and `evaluation_reasoning_effort`. Their defaults are `OPENROUTER_EVALUATION_MAX_TOKENS=8192` and `OPENROUTER_EVALUATION_REASONING_EFFORT=medium`. Pass `high` explicitly for the selected DeepSeek model. The assessment stage has a 180-second request timeout. Other stages keep their own model instances and token limits. Model construction leaves temperature unspecified, allowing each selected model's supported settings.

G-Eval uses `openai/gpt-6.1-terra` with medium reasoning, a 4096-token allowance, a versioned rubric, and threshold 0.8. Judge calls and their reported cost are recorded separately. Exact source IDs and quotations are checked independently of the judge. Langfuse scores attach to the HTTP request trace. The `PY-037/quiet-home-questions-v4` dataset compares recorded results and links them to the original HTTP traces. Publishing comparison records does not call the models again.

The [full-flow comparison](../tests/fixtures/agent-eval/quiet-home-with-granite/runs/2026-11-11-questions-v4-deepeval.json) retains upstream failures and the settings used for subsequent attempts. Its completed requests selected an unmarked conditional pair. The separate [granite–granite case](../tests/fixtures/agent-eval/quiet-home-granite-pair/README.md) exercises both authored conditions through the graph.

### Grounding catalog

The application reads the Typesense grounding_catalog collection, not the seed file, during semantic verification. Default GROUNDING_LANGUAGE=en and GROUNDING_CATALOG_VERSION=en-v1 select the current English pack.

- POST /api/v1/knowledge/grounding/reload replaces that language/version from fixtures/knowledge/grounding/grounding_en-v1.json (13 entries). Use explicitly for initialization or an intentional reset; it overwrites edits to that version.
- GET /api/v1/knowledge/grounding/search?q=agree searches definitions/examples for inspection.
- PUT /api/v1/knowledge/grounding/entries/{entry_id} accepts the full entry returned by search, with its text/label edited and identity/language/version preserved. Changes require no Python modification. The response returns the new snapshot hash.

Runtime loads all entries for the selected version. This is not top-k semantic proof. ground_question reuses evaluation_model_id; it makes at most one additional model call when typed agreement or candidate-type proposals exist. No such proposals means no catalog/model call. Bad IDs/quotes, incomplete decisions and technical failures prevent dependent planning; unverified agreements never become facts, and uncertain candidate-type filters never silently become a broader search. Langfuse records grounding_status, the catalog hash/entry IDs and decisions.

The held-out quality runner is tests/integration/test_grounding_model_evaluation.py. It requires explicit RUN_GROUNDING_EVALUATION=1 authorization and by default uses Luna with 8192 tokens/medium reasoning on ten questions in disposable Typesense. It saves prompts/observations, costs, outcomes and metrics under tests/fixtures/agent-eval/grounding-en/runs. Preparing or locally testing the runner does not call models. Source data provides a historical binary regex baseline; no legacy implementation runs. Current local tests verify contracts and source binding, not model semantic accuracy.
