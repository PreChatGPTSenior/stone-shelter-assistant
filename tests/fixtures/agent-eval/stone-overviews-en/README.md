# Named stone overview requests: missing route

Two authorized English requests against all eleven authored fixtures in disposable stores. Luna was configured for parsing/evidence and free Nemotron for other stages. Only Luna parsing was reached in each request. No production code, automatic model retry or semantic judge was introduced for these tests.

## Questions

“Tell me about Svetlana. Combine the stone's individual profile, general information from the encyclopedia, and the compatibility guide into a consistent overview. Distinguish individual facts from general type information, explain any apparent contradictions, and state what is unknown.”

The second question uses identical wording with Madame Obsidian instead of Svetlana.

- Svetlana: [raw run](runs/20261111T193805Z-svetlana-overview.json), [Langfuse trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/322eb62f92d137a9f005d16756d7d163).
- Madame Obsidian: [raw run](runs/20261111T193838Z-madame-obsidian-overview.json), [Langfuse trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/5fdf5c61c19223eddc9a65471b308f94).
- [Machine-readable outcomes](summary.json).

## Observations

Both requests returned HTTP 200 with unresolved_question and “Please clarify which stone or stone type you mean and what you would like to know.” Luna correctly returned named_stone and recommendation_limit=0. Missing collections defaulted to empty lists without parser errors. No current DTO field represents a named stone overview, and permitted_tools derived no supported goals. Planning therefore stopped without a planning generation, retrieval, card read, evidence generation or composed answer. Empty sources do not establish that the data was absent or contradictory: it was never requested from storage.

The existing graph supports bounded recommendations and explicit status/care/pair questions, rather than a generic overview. This is an unsupported-intent/completeness result, not a model's failed attempt to reconcile three supplied sources. The harness asserts HTTP success only; its passing status is not a semantic pass.

Reported Luna costs: Svetlana $0.000243975; Madame Obsidian $0.000242974999; total approximately $0.00048695. No other model stage ran.

## Required behavior for a later implementation

Add an explicit overview intent referencing the named stone, resolve its PostgreSQL card/current status, then use the verified type to read encyclopedia and compatibility-guide information. Compose individual facts and general type information as separate scopes, retain source references, show unknowns and conflicting evidence, and never infer an individual's character or household suitability solely from type rules. A general compatibility overview should not fabricate a specific household partner. Exact event details require a deliberate case-history lookup. Implement and test this route separately; these runs do not implement it.
