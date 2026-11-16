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

Integration tests use disposable Testcontainers and controlled embeddings, not persistent local data. Live model tests are skipped unless explicitly enabled. Scenario inputs and evaluation rubrics are under [agent-eval fixtures](../fixtures/agent-eval).

Search checks are linked to [acceptance criteria](search-acceptance.md). Use
`uv run pytest tests/unit --acceptance AC-EVIDENCE-01` to run associated unit checks,
or `uv run pytest --collect-only -q -m acceptance` to list all linked checks.
Repeat `--acceptance` to select several criteria; existing paid opt-in gates still apply.

### Frozen candidate-assessment replay

The opt-in runner is [test_candidate_assessment.py](../tests/evaluation/test_candidate_assessment.py). `RUN_CANDIDATE_ASSESSMENT_EVALUATION=1` enables paid calls. It replays a fixed current-contract input without parsing or retrieval. It uses `evaluation_model_id` from the shared `EVALUATION_MODEL_CONFIGURATIONS` list, with `reasoning_effort` and `max_tokens`. Full-run evaluation uses the same list; no previous model-list environment format is supported. Results are saved under `test-evaluation-results/candidate-assessment/<run_id>/` with manifest, result and observations files.

### Evaluation suites

Application evaluation runners live in `tests/evaluation`; their shared checks and judges live in `tests/evaluation/support`. Judge calibration on prepared answers and unit checks of evaluation infrastructure live in `tests/synthetic_evaluation`. Application unit tests are grouped by module under `tests/unit/assistant`, `tests/unit/search` and `tests/unit/core`; using a mocked model does not turn an application regression into judge calibration.

- `test_full_run_evaluation.py`: loads root `fixtures/` once per module into disposable Testcontainers, uses local Ollama and calls the workflow directly. `RUN_FULL_RUN_EVALUATION=1` explicitly enables paid calls. `EVALUATION_CASE_IDS` defaults to Q02,Q03,Q04; select any cases from the [scenario suite](../fixtures/agent-eval/questions-challenge-20/README.md). Results use `test-evaluation-results/<case_id>/<run_id>/` with a shared `manifest.json`.
- `test_saved_run_evaluation.py`: evaluates saved results offline. Run `SAVED_RUN_PATH=<result.json-or-run.json> uv run pytest -s tests/evaluation/test_saved_run_evaluation.py`. It writes a new timestamped report beside its input and asserts deterministic checks. It is skipped without a selected input; semantic answer quality remains unmeasured.
- `test_saved_run_geval.py`: grades a saved candidate-evidence generation with the original quiet-home GEval rubric. It requires `RUN_SAVED_RUN_GEVAL=1`, `SAVED_GEVAL_RESULT_PATH=<result.json>` and an explicit `OPENROUTER_GEVAL_MODEL`. The adjacent `observations.json` must contain the actual generation input/output and any referenced source documents. It never reruns the workflow. The 0.8 threshold is uncalibrated; this is evidence-extraction grading, not a general final-answer evaluation. Pytest checks that judging completed; the report records score, reason and the diagnostic threshold result. `GEVAL_ATTACH_LANGFUSE=1` additionally attaches the score to the source trace.
- `test_saved_run_ragas_eval.py`: evaluates saved Q01–Q20 answers and final sources with RAGAS Faithfulness, Response Relevancy, Context Precision and Context Recall. It requires `RUN_SAVED_RUN_RAGAS=1`, exactly one of `SAVED_RAGAS_RESULT_PATH=<result.json>` or `SAVED_RAGAS_SESSION_ID=<session>`, and an explicit `OPENROUTER_RAGAS_MODEL`. The optional `OPENROUTER_RAGAS_EMBEDDING_MODEL` defaults to `openai/text-embedding-3-small`; evaluator calls use OpenRouter and may incur charges. Reports use `<result-stem>-ragas-<timestamp>.json` beside each immutable result. Context Precision and Context Recall require separately curated factual references; reviewed required/forbidden assertions are never used as references. Supply them with `SAVED_RAGAS_REFERENCES_PATH=<references.json>` in this format:

  ```json
  {
    "references": [
      {
        "case_id": "Q01",
        "question": "The exact question captured in the saved Q01 result",
        "reference": "A separately reviewed factual answer for that question."
      }
    ]
  }
  ```

  The curated Q01–Q20 factual references are in [fixtures/agent-eval/ragas/references.json](../fixtures/agent-eval/ragas/references.json); their source and review policy are documented in the adjacent [dataset notes](../fixtures/agent-eval/ragas/README.md). The runner validates the case ID and exact saved question, rejects duplicate or malformed records and empty reference text before making evaluator calls, and records the reference file path and SHA256 in every report. Cases omitted from the file retain an explicit unavailable status for both reference-based metrics. Faithfulness is unavailable when a saved answer has no contexts, while Response Relevancy can still be scored. Metric execution errors are checkpointed and cause pytest to fail after all selected reports are saved. Scores are diagnostic only; no threshold is applied. It never reruns the workflow. Example invocation:

  ```sh
  RUN_SAVED_RUN_RAGAS=1 \
    SAVED_RAGAS_SESSION_ID=your-session-id \
    SAVED_RAGAS_REFERENCES_PATH=fixtures/agent-eval/ragas/references.json \
    OPENROUTER_RAGAS_MODEL=your-explicit-model-id \
    uv run --group eval pytest -s tests/evaluation/test_saved_run_ragas_eval.py
  ```
- `test_saved_run_jev_eval.py`: evaluates saved final answers selected by exactly one of `SAVED_JEV_RESULT_PATH=<result.json>` or `SAVED_JEV_SESSION_ID=<session>`. Session mode selects the Q01–Q20 archives and preflights every result, observation archive, criterion set and output path before its first paid request. It requires `RUN_SAVED_RUN_JEV_EVALUATION=1`, an explicit `JEV_MODEL` (for example `typesafe/jev-1.14`) and `OPENROUTER_API_KEY` in the process environment or project `.env`. DeepEval's native `JevEval` metric uses its own OpenRouter Jev model adapter; one request scores the reviewed required/forbidden answer criteria for each archive. The final answer is the only scored answer text; archived final sources and any saved workflow fields provide factual context, with missing fields recorded. Retrieval/evaluation-policy criteria that cannot be measured from a final answer are listed as `not_measured`. Reports are saved beside each immutable source as `<result-stem>-jev-<model-slug>-<shared-timestamp>.json`. The 0.8 threshold is uncalibrated and JevEval's score is not comparable to GEval's score. No application generation, fixture loading or indexing occurs.
- `test_grounding_model_evaluation.py`: evaluates only the real grounding stage on reviewed holdout cases with disposable Typesense. `RUN_GROUNDING_EVALUATION=1` enables paid calls; `GROUNDING_EVALUATION_MODEL` selects the model. Add `RUN_GROUNDING_ACCEPTANCE=1` to require every held-out outcome to match its reviewed label. This does not invoke or grade the parser. The [grounding fixture notes](../fixtures/agent-eval/grounding-en/README.md) explain the metrics.

- [`test_reference_answer_assertions.py`](../tests/synthetic_evaluation/test_reference_answer_assertions.py): calibrates a semantic judge on reviewed good/bad answers. `RUN_ANSWER_ASSERTION_EVALUATION=1` and an explicit `ANSWER_ASSERTIONS_JUDGE_MODEL` enable paid calls. The entire calibration uses one run/session; result, observations and manifest files are saved under `test-evaluation-results/reference-answer-assertions/<run_id>/`. It measures judge calibration, not application quality.
- [Jev model calibration](../tests/synthetic_evaluation/model_calibration/): offline payload/source checks run without a model. Six reviewed cases span all four evidence labels; one explicitly marked synthetic calibration-only report creates an unresolved conflict with a fixture observation. The small set does not establish broad judge quality. A paid OpenRouter run requires `RUN_JEV_MODEL_CALIBRATION=1`, `JEV_MODEL=typesafe/jev-1.14`, and `OPENROUTER_API_KEY` in the process environment or project `.env`. Optionally set `JEV_CALIBRATION_CASE_IDS` to comma-separated case IDs; the [calibration fixture notes](../fixtures/agent-eval/model-calibration/README.md) show the command selecting only the three added cases and describe the archive.

Shared model configurations are a JSON list in `EVALUATION_MODEL_CONFIGURATIONS`. Each entry has a unique `name`, main `model_id`, `evaluation_model_id`, `max_tokens` and `reasoning_effort`. The default is Luna 5.6 for main stages and Terra 5.6 for grounding/evidence. The calibration runner selects its judge explicitly instead of inheriting the application model.

For repeated comparisons, reuse `EVALUATION_COMPARISON_ID` and assign a new `EVALUATION_RUN_NUMBER` to each configuration execution. The full-run suite numbers configured model configurations consecutively from that number. Without an explicit comparison ID, an invocation starts a new comparison; the default run number is 1.

```sh
export EVALUATION_COMPARISON_ID=challenge20-model-study
export EVALUATION_RUN_NUMBER=1
```

These variables only label a run; model calls still require explicit authorization and the runner's opt-in flag. Each full run uses session `STPY-<comparison_id>-r<run_number>` with at least two digits for the number. API comparison requests must send that session in `X-Session-ID` and both `comparison_id` and `run_number` in the JSON body. Find the run in Langfuse by session or comparison metadata; use each saved case's `trace_id` to inspect one question. Workflow results include a `configuration_id` derived from effective model settings; judge settings are recorded separately.

Evaluation datasets use `STPY-<suite-name>` (for example `STPY-quiet-home-candidate-assessment`). Dataset item IDs include the dataset name, case and input hash. Datasets identify fixed inputs; sessions identify executions. All run outputs belong in root `test-evaluation-results/`.
