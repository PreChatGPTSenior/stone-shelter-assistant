# Quiet neighbors and Svetlana: parser-contract failure

One authorized request using all eleven authored stone cards in disposable PostgreSQL/Typesense/Qdrant services. Luna was selected for parsing and assessment; free Nemotron for planning, selection and answer. Only the parsing model was reached. No semantic judge or model retry ran, and application/test source was not changed.

Question: «Подбери до трёх камней для тихого дома. Соседи не терпят громких звуков по утрам, поэтому камень обязательно должен вести себя тихо ранним утром. Кто сейчас доступен и почему может подойти?»

[Raw request, response and observations](runs/20261111T185344Z.json).
[Langfuse trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/b7bdd36e750bc2b58e8bfba00e46e9f7).

## Observed outcome

- Fixture loading confirmed two shelters and eleven stones, including Svetlana.
- Luna returned preferences with character=[] but omitted the required compatibility list.
- Pydantic reported preferences.compatibility: Field required. A local replay of the raw tool arguments reproduced the validation failure without a model call.
- parse_question returned invalid_criteria; plan_tools returned unresolved_question. HTTP returned 200 with a clarification message.
- Grounding checks, Typesense/Qdrant retrieval, RRF, candidate selection and evidence assessment were not reached. This record establishes no result about Svetlana's suitability or the model's ability to interpret her singing.
- The experimental harness asserted HTTP success only, so its pytest exit code was zero. That is not a semantic success for this scenario.
- One Luna generation reported $0.000306825. There were no free-model generations or evidence-assessment generations.

The first launcher was skipped by the paid-test opt-in guard and made no model calls; the recorded run is the single actual request. The corpus is eleven stones, while normal retrieval/assessment still uses the configured engine and shortlist limits, not exhaustive assessment of all eleven.

## Relation to question_grounding.py

Grounding runs after the parsed DTO validates. It checks explicit positive candidate-type phrases and the two supported decision-agreement propositions using conservative English/Russian patterns. It neither ranks stones nor contains special handling for Svetlana, singing or windowsills. Its checks could not run on this incomplete DTO. Indexed en/AVAILABLE filters are built separately in selection.py.

Next work is the parser's empty-list contract or output-format handling, followed by a separately authorized request. No fix or repeat was applied during this experiment.
