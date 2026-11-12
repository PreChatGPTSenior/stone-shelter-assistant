# Quiet-home hybrid search: ten Luna assessments

Ten authorized end-to-end requests for the same question:

> Подбери до двух камней для тихого дома, где уже есть гранит. Кто сейчас доступен и почему может подойти?

Luna (`openai/gpt-6-luna`, medium reasoning, 8192 output-token allowance) handled evidence assessment. Terra (`openai/gpt-6.1-terra`) handled parsing, planning, candidate selection and answer generation. Embeddings used local `qwen3-embedding:0.6b`. All requests used the same authored fixtures in disposable PostgreSQL/Typesense/Qdrant containers. Maximum request concurrency was two; the runner did not retry question requests.

No application or test source was changed for this experiment. The existing opt-in HTTP test was configured in memory for ten Luna cases. The semantic judge was disabled, and experiment-dataset publication was replaced with local result archival. The inherited runner records intentional judge skips in judge_error and may leave a failed deepeval_character_entailment observation; these are not application or Luna failures. There were no judge-model calls.

## Records

- [Raw run](runs/20261111T145558Z.json): requests, responses, assessments, reconstructed model inputs, source documents, checks, DTO schemas and exported Langfuse observations.
- [Summary](summary.json): aggregate results, trace IDs, exact raw-run hash, source-file hashes and base Git commit. The working tree contained the uncommitted hybrid implementation, so the base commit alone does not identify the executed code.

## Observed results

| Check | Result |
| --- | --- |
| HTTP success | 10/10 |
| Parsed assessments with nonempty character findings | 10/10 |
| Exact candidate/source/quote checks | 10/10 |
| Invented household agreements | 0 |
| Granite condition checks | 20 unknown checks (two per run) |
| Madame Obsidian | recommended in 10/10 |
| Sir Pebble | conditional_option in 10/10 |

The UUID-as-source_ref error did not recur. This is one question repeated end to end, not ten different scenarios. Parsing produced ten distinct prepared query/filter records and five distinct engine-ranking patterns. Final candidate dispositions were stable. This does not establish general model reliability or isolate the effect of the new source contract from other workflow changes.

Reported model costs: Luna $0.00278991, Terra $0.09243200, total $0.09522191. These sum the fifty generation observations; local embeddings and infrastructure are not included.

## First request: actual retrieval path

The parser treated quiet-home fit as a requirement, the existing granite as a household fact, and requested up to two recommendations. It prepared English lexical and semantic queries with indexed AVAILABLE filtering and no candidate-type filter.

| Stone | Typesense rank | Qdrant rank | RRF score | Final disposition |
| --- | ---: | ---: | ---: | --- |
| Madame Obsidian | 1 | 2 | 0.03252247488101534 | recommended |
| Sir Pebble | absent | 1 | 0.01639344262295082 | conditional_option |

The fused pool contained five stones. Selection retained Madame Obsidian and Sir Pebble and explicitly left the other three unselected. PostgreSQL confirmed both were AVAILABLE. Luna bound quiet-home quotes to biography and profile.preferred_environment, leaving individual type-specific compatibility findings empty. The graph applied HARMONIOUS to granite/obsidian and retained CONDITIONAL for granite/granite because both agreement checks were unknown.

Langfuse records parse_question → plan_tools → search_candidates → tools/search_stones_hybrid → typesense_search + qdrant_search → rrf_fusion → select_candidates → read_candidate_cards → verify → evaluate_candidates → answer. Engine ranks, contributions, selection decisions and final evaluations can be followed by the same internal ID within the trace.

## Request traces

| Request | Trace |
| --- | --- |
| 1 | [7d64b25869e22e88dd7685774e72c516](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/7d64b25869e22e88dd7685774e72c516) |
| 2 | [ac7f44d1c856fd6a3c3765aeaf3fde7a](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/ac7f44d1c856fd6a3c3765aeaf3fde7a) |
| 3 | [b2d2659246173fb2bbfacd69525f4fe9](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/b2d2659246173fb2bbfacd69525f4fe9) |
| 4 | [420cb9f9fc2ecef20329ea76459d5f72](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/420cb9f9fc2ecef20329ea76459d5f72) |
| 5 | [7aab72f77090473b57448a07860bc7ef](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/7aab72f77090473b57448a07860bc7ef) |
| 6 | [cb7422b717afd43e598aaadcb9e9ed78](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/cb7422b717afd43e598aaadcb9e9ed78) |
| 7 | [445bb376b5fe0fcb4091f7df927cbfd6](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/445bb376b5fe0fcb4091f7df927cbfd6) |
| 8 | [79d554b6e13912d4bd47b47e17044f77](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/79d554b6e13912d4bd47b47e17044f77) |
| 9 | [c08d2fcc64d89f684759a8910cb43300](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/c08d2fcc64d89f684759a8910cb43300) |
| 10 | [2eda81176373f3d710f3252bc6410324](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/2eda81176373f3d710f3252bc6410324) |
