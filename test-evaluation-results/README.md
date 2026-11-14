# Run files

The full-run suite groups results by question and run:

```text
test-evaluation-results/
  manifest.json
  Q02/
    STPY-<comparison_id>-r01/
      result.json
      observations.json
  Q03/
    STPY-<comparison_id>-r01/
      result.json
      observations.json
```

`manifest.json` lists run settings, fixture/code hashes and paths to case results. Each `result.json` contains the question, workflow result, captured state and local stage checks. Each `observations.json` contains the Langfuse export and its capture status.

The earlier walkthrough keeps all its files in one named run folder. Five files share a long prefix: the comparison name, `r01` and the start time. Their endings identify their purpose:

| File | Contents and purpose |
| --- | --- |
| `…-challenge20.json` | Main run archive: Q04, model settings, fixture/code hashes, HTTP response, `trace_id` and final graph state, including criteria, candidates, evidence, decisions and answer. It lets us inspect the result without another paid call. |
| `…-observations.json` | The 32 observations exported from Langfuse: stages, tool calls and model generations, their inputs/outputs, parent links, timing, usage and cost. More detail than the main archive. |
| `…-evaluation.json` | Local checks of the saved result: stage coverage, evidence, decisions and scenario expectations. Produced by the offline evaluator; no new model calls or GEval grading. |
| `…-pytest.log` | Technical pytest output: runner completion, messages and errors. Useful for diagnosing the execution. |
| `…-walkthrough.md` | A readable Markdown walkthrough of observation inputs and outputs. A learning aid generated from the saved data. |

Saved walkthrough inputs retain their original paths and hashes as provenance. Those paths describe the execution before the fixture relocation. Current inputs are under root `fixtures/`.
