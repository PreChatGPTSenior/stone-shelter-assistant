# Hybrid search: free upstream stages with Luna parsing and assessment

Ten end-to-end repeats of the same quiet-home-with-granite question, with maximum concurrency two and no question retries. All authored fixtures were loaded into disposable PostgreSQL/Typesense/Qdrant containers.

| Stage | Model |
| --- | --- |
| Parse question and prepare retrieval | openai/gpt-6-luna |
| Plan tools | nvidia/nemotron-3.5-super-vl:free |
| Select candidates | nvidia/nemotron-3.5-super-vl:free |
| Extract assessment evidence | openai/gpt-6-luna |
| Generate explanation | nvidia/nemotron-3.5-super-vl:free |

Assessment retained medium reasoning and an 8192-token allowance. Other stages retained the application limit of 3072 tokens. Embeddings used local qwen3-embedding:0.6b.

## Outcomes

- HTTP 200: 10/10. Expected graph decisions (Madame Obsidian recommended, Sir Pebble conditional): 7/10.
- Luna evidence assessment was reached in seven requests; all seven had valid exact source references and quotations.
- Three requests returned no candidates; the scenario assertions failed and pytest exited 1.
- Request 4: Luna invented the PREFERS_SOLITUDE filter and two negative agreement facts. The filter excluded all available stones.
- Request 6: the free selection model consumed 3072 reasoning tokens and emitted no JSON, yielding invalid_selection. Luna had also omitted quiet-home character criteria.
- Request 7: Luna generated language=English instead of the indexed en, excluding every card in both engines.
- Three answer texts exposed internal UUIDs. Request 2 also incorrectly described only one stone as available despite both verified statuses being AVAILABLE. Correct graph decisions therefore do not certify answer prose.

The source code hashes match the [previous Terra-upstream series](../quiet-home-hybrid-luna-10/summary.json), and no application/test code was changed. However, parsing changed from Terra to Luna as well as downstream stages changing to a free model. The observed difference cannot be attributed solely to free models.

## Records and costs

[Raw run](runs/20261111T150631Z.json) stores actual requests/responses, assessments, exact checks, model inputs, schemas and trace observations. [Telemetry refresh](runs/20261111T150631Z-telemetry-refresh.json) completes the last request's generation export after ingestion delay; no model call was repeated. [Summary](summary.json) stores hashes, per-request outcomes and costs.

Seventeen Luna calls reported $0.00309671 in total. Twenty-five Nemotron calls used the :free endpoint, whose prompt/completion prices were zero in the OpenRouter catalog preflight. Those observations have no explicit total-cost field; do not interpret missing telemetry as a reported zero.

No paid semantic judge ran. The inherited runner records intentional judge skips as judge_error and may mark the corresponding judge observation as an error. These are separate from the actual workflow failures above. No experiment dataset was published.

## Traces

| Request | Outcome | Trace |
| --- | --- | --- |
| 1 | Expected graph decisions | [ec9144d326b53c268dd9341685923eea](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/ec9144d326b53c268dd9341685923eea) |
| 2 | Expected graph decisions | [83b79d59c852194cdaa21d04451017af](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/83b79d59c852194cdaa21d04451017af) |
| 3 | Expected graph decisions | [093187a9b90f7fd00bb103f9ef854658](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/093187a9b90f7fd00bb103f9ef854658) |
| 4 | No candidates — see diagnosis | [473445f8ebfba05fae1e421c0382d873](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/473445f8ebfba05fae1e421c0382d873) |
| 5 | Expected graph decisions | [b6abfb50b6a2f72f2f8ccf350215653c](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/b6abfb50b6a2f72f2f8ccf350215653c) |
| 6 | No candidates — see diagnosis | [c0e6150a46cd4e2e5458023fd096aec4](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/c0e6150a46cd4e2e5458023fd096aec4) |
| 7 | No candidates — see diagnosis | [054acaeade9e72253c283711716bee71](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/054acaeade9e72253c283711716bee71) |
| 8 | Expected graph decisions | [d6445abf2f8a090e9310ae8b620fa929](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/d6445abf2f8a090e9310ae8b620fa929) |
| 9 | Expected graph decisions | [a3dfadf00877e3df5e9965e7948d489d](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/a3dfadf00877e3df5e9965e7948d489d) |
| 10 | Expected graph decisions | [f3641cc4ce2d8b05aadde544609341fe](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/f3641cc4ce2d8b05aadde544609341fe) |

This experiment evaluates one repeated question, not the twenty-scenario corpus. The next issues to investigate are grounding exact filters and agreement facts during parsing, free-model output budgets/settings, and constraints on generated explanation text. No fixes were applied during the experiment.
