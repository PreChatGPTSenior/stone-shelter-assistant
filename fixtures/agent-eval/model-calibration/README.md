# Jev evidence calibration

[cases.json](cases.json) contains six reviewed claims: three fixture-derived `INSUFFICIENT_EVIDENCE` cases, one `SUPPORTED` case, one `CONTRADICTED` case, and one `CONFLICTING_EVIDENCE` case. The conflict case combines a fixture observation with a distinct synthetic calibration-only witness report. The synthetic source is labeled in both the case and result archive and is not part of authored stone history.

The cases cover an observation date that does not prove behavior onset, a granite type description that cannot establish an individual's preference when the profile is absent, household agreements explicitly scoped to BASALT+GNEISS rather than GRANITE+GRANITE, direct individual support and contradiction, and unresolved incompatible reports about the same person in the same session. The two reports in the conflict case have equal authority and neither supersedes or corrects the other. Fixture-derived sources are loaded from their original fixtures; the synthetic report has a separate source ID and explicit provenance note.

The judge distinguishes `SUPPORTED`, `CONTRADICTED`, `CONFLICTING_EVIDENCE`, and `INSUFFICIENT_EVIDENCE`. Apply subject and pair scope before detecting conflict. Conflicting evidence means incompatible evidence at the same applicable scope and authority; missing evidence, indirect evidence, silence, and evidence scoped elsewhere are insufficient, not conflicting. Absence is not negation. An observation timestamp is not an onset date. Do not use outside knowledge.

Expected labels and rationales are stored in the fixture and output archive only; `decision_payload` sends neither. It sends the claim and fixture-derived source texts plus one Jev `choice` question. The response validator requires exactly one answer, all four label probabilities, a valid confidence, approximately normalized probabilities, and nonnegative token usage.

## Local checks and optional model run

Offline tests run without credentials or network access:

```sh
uv run pytest -q tests/synthetic_evaluation/model_calibration
```

The optional paid run uses OpenRouter's Decisions API and the pinned Jev model. It requires an explicit opt-in and model name; the runner reads `OPENROUTER_API_KEY` from the process environment or the project `.env` (without overriding an existing process value):

```sh
export RUN_JEV_MODEL_CALIBRATION=1
export JEV_MODEL=typesafe/jev-1.14
export JEV_CALIBRATION_CASE_IDS=sir-pebble-quiet-evenings,madame-obsidian-vacuum-anxiety,quartzless-synthetic-same-session-conflict
uv run pytest -q -s tests/synthetic_evaluation/model_calibration
```

`JEV_CALIBRATION_CASE_IDS` is optional; when unset, all six cases run. Set it to a comma-separated list of known case IDs to select cases. Empty entries, duplicate IDs and unknown IDs fail before any request is sent. The command above selects only the three added cases.

The runner posts to OpenRouter's [`POST /api/alpha/decisions` API](https://openrouter.ai/blog/insights/what-is-jev/) using `typesafe/jev-1.14`. Archives include the requested and returned model IDs, provider, request ID, choice probabilities, expected labels, mismatches, token usage and cost, and fixture/code SHA-256 hashes under `test-evaluation-results/jev-model-calibration/<run_id>/`. The API key is used only in the authorization header and is not archived. Each result identifies its case and source provenance, including the mixed fixture-plus-synthetic case. Any mismatch or malformed/failed response leaves the partial run record and fails the optional test.
