# Quiet-home candidate assessment

Reference records from past experiments only. Their DTOs and input formats are not supported by current code. Use the maintained current-contract fixture at `tests/fixtures/assistant/quiet-home-assessment.json` for new assessment runs; the archived runs below do not describe results for that updated fixture.

This PY-037 case preserves the evidence-assessment input that Dots failed to complete at 3072 output tokens and the six-model comparison at 8192 output tokens on November 11, 2026.

## Stored data

- [input.json](input.json) is a byte-for-byte archival copy of the fixture consumed by the current replay test. It contains the original model messages, DTO schema, parsed criteria, two stone cards, recorded PostgreSQL statuses, source documents, fixture version, and source trace IDs.
- [runs/2026-11-11-8192.json](runs/2026-11-11-8192.json) contains seven attempts across six models, including the initial Dots provider error and its completed retry. It preserves returned DTOs, per-candidate evaluations, check results, reported token usage, elapsed times, reported costs, and Langfuse experiment and trace links.
- The current test still reads [the original runner fixture](../../assistant/quiet-home-assessment.json). Its Python path can be migrated separately. The archival input has the same SHA-256 as the original file.

The original failed observation belongs to [source trace 17b4b712756b6168102f0d40683616e7](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/17b4b712756b6168102f0d40683616e7). Comparison runs use the Langfuse dataset `PY-037/quiet-home-candidate-assessment` and session `2026-11-11-PY-037`.

## Fixed scenario

The question is “Подбери до двух камней для тихого дома, где уже есть гранит. Кто сейчас доступен и почему может подойти?”

The frozen candidates are Sir Pebble and Madame Obsidian. Both were recorded as `AVAILABLE`. The frozen parser result classifies the quiet-home criterion as a preference and the presence of granite as a household fact. Parsing and search are excluded from this isolated comparison. Every model receives the same recorded messages and DTO schema.

Both biographies explicitly support quiet or peaceful surroundings. Madame Obsidian's profile also states a preference for a quiet home with a predictable routine. Neither card provides granite-specific individual compatibility evidence. The household fact that granite is present does not establish arrangements required by the conditional granite–granite rule.

## Generation settings

Each call allows 8192 output tokens and requests strict JSON Schema output. DeepSeek requests `high` reasoning because the selected model does not advertise `medium`. The other five models request `medium`. The shared name of an effort level does not establish equal computation across providers.

Ordinary test runs skip the live experiment. Reproduction commands and the optional single-model selector are documented in [setup.md](../../../../docs/setup.md#frozen-candidate-assessment-replay).

## Recorded results

All six completed calls returned DTOs that passed schema validation. Two responses also passed every scenario check.

| Model | Reasoning tokens | Total output tokens | Estimated visible tokens | Seconds | Reported USD | Scenario checks |
|---|---:|---:|---:|---:|---:|---|
| GPT-6 Luna | 700 | 889 | 189 | 14.41 | 0.000585675 | Candidate IDs and source references were confused |
| DeepSeek V4.1 Flash | 6576 | 6857 | 281 | 35.58 | 0.004638790 | Unsupported accommodation confirmation |
| Claude Sonnet 5 | 970 | 1419 | 449 | 15.18 | 0.018950000 | Unsupported accommodation confirmation |
| Gemini 3.8 Flash | 1942 | 2180 | 238 | 15.22 | 0.009312750 | Passed |
| GPT-6.1 Terra | 156 | 400 | 244 | 5.62 | 0.003411750 | Passed |
| Dots3 Note Preview free | 6168 | 7787 | 1619 | 81.41 | 0 | Invalid source references and reversed character findings, plus unsupported accommodations |

Total reported cost for completed calls was USD 0.036898965. The first Dots attempt returned a provider error before a DTO and has no reported usage or cost. Its attempt is retained in the run file.

Reported output-token totals include reasoning. The visible-token estimate is the difference between the provider-reported total output and reasoning counts. It is not a separate tokenization of the returned JSON.

## Interpretation and checks

At 8192 tokens, Dots completed a DTO after using 6168 reasoning tokens. DeepSeek used 6576 reasoning tokens before a much shorter DTO. These observed reasoning counts exceed the previous 3072-token combined output allowance. Luna, Claude, Terra, and Gemini completed using fewer tokens in this case.

Completion, schema validity, evidence grounding, and scenario correctness are recorded separately. Longer reasoning did not establish correctness. Luna's schema-valid DTO used stone types as candidate IDs and UUIDs as source references. Claude treated the existing-granite fact as confirmation of conditional arrangements. DeepSeek supplied the household quote where a quotation from the pair rule was expected. Terra and Gemini preserved the required identifiers and quotes and left unsupported compatibility findings empty.

The live test checks exact candidate/source references and quotes, character coverage for both candidates, and the absence of unsupported compatibility claims. It deliberately fails when any model fails a scenario check. The comparison covers one frozen case and one completed response per model, so it does not establish general model rankings or repeated-run reliability.

## Full-flow comparison with DeepEval

The subsequent [v4 HTTP comparison](runs/2026-11-11-questions-v4-deepeval.json) records thirteen HTTP attempts and six completed assessments. Its [input manifest](inputs/2026-11-11-questions-v4.json) preserves the actual prompt, two-list DTO schema, criteria, cards, and sources separately for each completed assessment. These are new inputs rather than replacements for the original frozen replay.

All six completed calls returned parsed assessments without inventing household agreements. Luna, Terra, Claude, and Gemini received G-Eval 1.0. DeepSeek and Dots received 0.2. The judge was Terra, including for the evaluated Terra response, so the comparison is exploratory. Exact source-reference checks are stored independently of G-Eval.

The upstream free planner exhausted its output limit on four attempts. Further attempts changed planning to Luna. Search-provider errors and an empty shortlist required another subset of requests with Terra on search, parsing, selection, and answer. The report retains the source traces and upstream variants. Candidate selection was rerun, so this full-flow comparison is distinct from the fixed-input six-model experiment.

The completed requests selected Madame Obsidian and Homeward Pumice. The granite–pumice rule is unmarked, and its condition list was empty. The rule remained conditional with `conditions_status=unmarked`. The [separate granite–granite case](../quiet-home-granite-pair/README.md) verifies the two annotated conditions under an actual graph run.

## Future records

Keep this input and run immutable. Store later runs as new files under `runs/`, with generation settings, snapshot hash, all attempts, reported usage and cost, scenario checks, returned DTOs, and Langfuse links. A changed prompt, DTO schema, criterion interpretation, or source selection requires a separately versioned input snapshot and its own hash. Compare responses against reviewed expectations rather than treating a prior model response as ground truth.
