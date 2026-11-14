# Stone Shelter Assistant

A learning application for practicing LLM search and evaluating agent workflows. The fictional stone shelter provides a small, deliberately challenging dataset; production completeness is outside this exercise.

## Four knowledge sources

The learning dataset is supplied through prepared stone and reference fixtures. The sources deliberately contain conflicting claims and signals so we can evaluate how search, evidence extraction and answers handle them.

| Source | What it describes |
| --- | --- |
| Individual cards and profiles | A specific stone's biography, preferences and traits. |
| Shelter observations | Recorded behavior and case events, including evidence that may contradict the profile. |
| Encyclopedia | General geological information, type descriptions and care guidance. |
| Compatibility guide | Fictional type-pair verdicts, explanations and conditions for living together. |

Individual cards and observations are loaded from [stone fixtures](../fixtures/stones) into PostgreSQL and projected into the search engines. The [encyclopedia](../fixtures/knowledge/stone-encyclopedias) and [compatibility guide](../fixtures/knowledge/type-compatibility) are indexed from authored reference files.

Individual evidence and general type knowledge keep separate identities. Profile/preferences have priority over observations for character assessment; general descriptions do not establish an individual's behavior. PostgreSQL supplies current availability, while the compatibility guide supplies type-pair rules.

## Current search

The model parses an English question into typed requests and criteria. Parser and auditor share one snapshot of an editable semantic concept catalog. Typesense and Qdrant retrieve candidate cards in parallel; a small Python RRF function merges their ranks. An LLM chooses a shortlist, then the workflow reads cards, observations and relevant reference knowledge.

The model extracts source-bound quotations. Python verifies source binding, current availability and compatibility conditions, calculates the final ranking and renders the result with sources. Langfuse records the stages, candidate provenance and model calls. Named information and exact pair questions have dedicated lookup routes.

## Accepted compromises

- **Fixture loading follows a happy path.** Prepared records and explicit reload endpoints support the learning dataset. A production ingestion pipeline, complete CRUD, automatic recovery and atomic updates across stores are not implemented.
- **Transparent rank fusion.** RRF is a small deterministic function, not a custom ranking framework. A cross-encoder reranker has not been added or compared; it would be a separate step from rank fusion. The current LLM shortlist is also an experimental choice.
- **Limited search coverage.** The pilot retrieves cards first and reads observations for shortlisted stones. A fact found only in an observation may therefore fail to discover its stone. Not every card field is available to evidence assessment.
- **Partial validation.** Selected scenarios and local tests pass, but search and free-form answers have not been exhaustively checked across edge cases, paraphrases or long contexts. Valid source IDs and quotations do not guarantee semantic correctness or completeness.
- **Bounded scope.** Active questions, fixtures and prompts are English-only. Production hardening and multilingual behavior are deferred.

The authored scenarios, reviewed expectations and judge rubrics are the starting point for new evaluation runs and comparisons of retrieval and selection strategies.

The current learning phase focuses on evaluation of the existing workflow: reviewed baselines, Langfuse trace inspection, DeepEval judge calibration, routing checks and Ragas retrieval/context metrics. Comparison and run identifiers connect model configurations, local archives and Langfuse traces; this instrumentation does not establish answer quality. Remaining work is tracked in the [open evaluation issues](https://github.com/PreChatGPTSenior/stone-shelter-assistant/issues?q=is%3Aissue+is%3Aopen). CRUD expansion, production recovery, alternative backend implementations and Java reproduction are deferred.

See [setup](setup.md) for local commands.
