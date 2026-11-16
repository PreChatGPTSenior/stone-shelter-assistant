# Curated RAGAS references

`references.json` contains separately authored factual answers for the English Q01–Q20 scenario questions. Each record keeps the question text identical to `questions-challenge-20/scenarios.json` because the saved-run evaluator matches references by both case ID and exact question.

The answers were curated from the individual records in `fixtures/stones/`, the current `adoptionStatus` values in those records, the relevant pairings in `fixtures/knowledge/type-compatibility/stone-type-compatibility_en.json`, and the limestone care chapter in `fixtures/knowledge/stone-encyclopedias/stone-encyclopedia_en.md`. Unknown or unconfirmed facts remain unknown; type-level compatibility stays distinct from individual behavior, and event history does not override current availability. References do not copy model transcripts or the scenario evaluation rubrics. Review the dataset when the corresponding source fixtures or scenario questions change.
