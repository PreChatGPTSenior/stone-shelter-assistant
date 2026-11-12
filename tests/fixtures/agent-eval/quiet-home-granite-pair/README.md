# Granite–granite condition check with Luna

Reference record from a past experiment only. Its input schema is not a supported current replay contract. Current tests construct inputs using the current DTO and maintained assessment fixture.

This PY-037 case targets the annotated pair through `POST /api/v1/questions`. The question is “Подбери одного гранитного камня для тихого дома, где уже живёт другой гранит. Кто сейчас доступен и почему может подойти?”

The evaluation model is `openai/gpt-6-luna`, with medium reasoning and an 8192-token allowance. Terra handles parsing, search, selection, and answer. Luna handles planning. The request uses authored fixtures in disposable Testcontainers and selects Sir Pebble, a granite stone recorded as `AVAILABLE`.

The parser extracts the existing granite from the question and no typed agreement facts. The graph reads the authored granite–granite conditions and records both checks.

| Condition ID | Status | Matching facts |
|---|---|---|
| `rotate_decisions` | `unknown` | `[]` |
| `decision_deadline` | `unknown` | `[]` |

The pair retains `CONDITIONAL`, with `conditions_status=unconfirmed` and `policy_rule=conditions_unconfirmed`. The answer includes “Условия не подтверждены.” The test explicitly requires both condition IDs and their `unknown` statuses, so an empty condition list cannot pass this case.

The [Langfuse request trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/0ad484bca31583320d8ef90b1ba4e834) contains the checks under `evaluate_candidates → candidate_evaluations → reasons → condition_checks`. It belongs to session `2026-11-11-PY-037`.

## Input and result

- [input.json](input.json) preserves the assessment messages and schema, parsed criteria, recorded Sir Pebble card, source documents, fixture version, and source trace ID.
- [runs/2026-11-11-luna.json](runs/2026-11-11-luna.json) preserves the returned DTO, candidate evaluation, exact condition checks, request model selections, G-Eval result, and independent source-reference check. It references the input SHA-256.

## Separate character-evidence failure

Luna returned an accurate quotation about enjoying quiet evenings and marked it `confirmed`, but used Sir Pebble's UUID as `source_ref` instead of `biography`. The application rejected the unmatched source reference. With character fit parsed as a requirement, the graph excluded the candidate for `requirement_not_met`.

G-Eval returned 1.0 and incorrectly stated that the source reference matched. The independent exact source-reference check returned false. The condition verification passed, while the candidate's character-evidence binding failed. This case demonstrates why semantic judge scores and structural/source checks must remain separate.

Reproduction parameters for the opt-in integration test are documented in [setup.md](../../../../docs/setup.md#full-questions-flow-with-deepeval).
