# Twenty future questions scenarios

This versioned specification contains three existing baselines and seventeen new cases over all eleven operational stone fixtures (nine distinct types: two records are GRANITE and two are MARBLE). Svetlana is a loud early-morning singer and a negative quiet-home example in Q02. It contains **no model-run results**. Historical assessment inputs and runs remain unchanged.

[scenarios.json](scenarios.json) is the machine-readable manifest. Active questions use English only during stabilization. The first three are English versions of prior baselines; historical records retain their original wording. Expected behavior and evaluation instructions are in English.

## Coverage and questions

| ID | Focus | Question |
| --- | --- | --- |
| Q01 | status_and_compatibility | Is Madame Obsidian available and compatible with granite? |
| Q02 | recommendation | Find up to two stones for a quiet home where a granite stone already lives. Who is currently available and why might they fit? |
| Q03 | recommendation | Find one granite stone for a quiet home where another granite stone already lives. Who is currently available and why might they fit? |
| Q04 | recommendation | Find one granite stone for a quiet home where granite already lives. We have agreed to take turns on small decisions and established a deadline for shared decisions. |
| Q05 | recommendation | Find one granite stone for a quiet home with our granite. We agreed to take turns on small decisions. We have not decided anything about a deadline for shared decisions yet. |
| Q06 | recommendation | Find one granite stone for a quiet home with our granite. We want to agree on rotating decisions and deadlines someday, but we have not done so yet. |
| Q07 | recommendation | Find one granite stone for a quiet home with our granite. We agreed to take turns on decisions, but refused to set a deadline for shared decisions. |
| Q08 | recommendation | Find one granite stone for a quiet home with our granite. We agreed to rotate decisions and set a deadline for shared decisions only for the basalt-gneiss pair. These agreements do not apply to granite pairs. |
| Q09 | recommendation | Find one obsidian stone. The stone must tolerate a vacuum cleaner calmly because we use it daily. Enjoying human company is a preference, not a requirement. |
| Q10 | recommendation | Find one gneiss stone for a family with children. Being good with children is required. Enjoying garden visits is only a preference. |
| Q11 | recommendation | Find one slate stone for a home with loud music. Calm behavior around music is required. I have caregiving experience. |
| Q12 | status_and_evidence | Captain Basalt met a family who enjoy quiet board games. Does that mean the stone likes quiet surroundings, and can I adopt him now? |
| Q13 | status_and_evidence | Can I adopt Sunny Marble now? An old note says he is available. Does the name Sunny prove that he has a cheerful personality? |
| Q14 | status | Mossy Limestone was reserved. Is he still reserved or can I adopt him now? I need the current status. |
| Q15 | status_and_location | Wandering Sandstone has case number 0008-2026-P1. Is he currently at P1 or P2, and can I adopt him? |
| Q16 | recommendation | Find one pumice stone for a home where granite already lives. Is enjoying the company of other stones enough to prove compatibility with granite? |
| Q17 | recommendation | Find one granite stone whose biography or profile explicitly confirms a preference for a quiet home. The name Professor Quartzless and a large number of observations alone are not evidence. |
| Q18 | multi_candidate_comparison | Compare Sir Pebble and Professor Quartzless. Are both available, and whose biography specifically says he enjoys quiet evenings? Do not transfer one stone's description to the other. |
| Q19 | history_and_status | Why was Velvet Slate returned, what care followed the return, and is he currently available? Put the events in chronological order. |
| Q20 | care | Mossy Limestone is limestone. Can I clean him with vinegar and keep him on a constantly wet shelf? What does the encyclopedia say, and are any individual care needs recorded? |

## Evaluation contract

Run each question independently through POST /api/v1/questions after an explicitly authorized model run. Use all eleven authored stone records and both knowledge sources in disposable storage. Preserve stable external IDs and resolve internal IDs afresh in each run. The focus_stone_ids list identifies relevant coverage and counterexamples, not a mandatory exact shortlist. The current shortlist cap remains three.

Score stages separately:
1. Retrieval: was necessary positive or conflicting evidence retrieved? Empty search results cannot pass a negative-character scenario merely by avoiding recommendations.
2. Parsing: hard requirements, preferences, existing household members, actual agreements, denials and pair scope.
3. Routing: did the graph cover all requested intents and entities? A correct status with an unanswered history question is incomplete.
4. Grounding: exact candidate/source/quote binding and criterion fragment. Run deterministic checks before semantic grading. Valid labels alone do not establish source presence or quotation support.
5. Policy: current PostgreSQL availability, conditions and candidate disposition. A conditional option is not an unconditional recommendation.
6. Answer: all requested parts, supported explanations and explicit uncertainty. Use a semantic judge only for meaning; it cannot override failed identifier checks.

The expected.required and expected.forbidden entries are evaluation requirements, not executable assertions or observed successes. The pair and condition_checks entries provide structured expectations for a future runner. The local manifest tests check coverage and consistency with authored fixtures; they do not test model reasoning or end-to-end search.

Keep requirement inference separate from evidence extraction. Q02 intentionally does not impose a single exact ranking. Q03 isolates the archived source_ref failure. Q04 is a positive control; Q05–Q08 vary missing facts, intention, denial and scope. Q09–Q11 separate required and optional traits from availability. Q12–Q20 cover stale events, misleading names, transfers, missing profiles, multiple entities and material care.

## Known capability boundaries

The current reference planner supports a single named stone and does not expose event history as a planned step. Q12, Q18 and Q19 deliberately probe these limits. Q13 and Q20 also request individual evidence that a status/encyclopedia-only route cannot fully establish. Record these as capability or completeness failures if encountered, rather than relaxing expectations or attributing every failure to the evaluation model.

Professor Quartzless has 99 observation events plus admission. Those event texts are not sources in the current candidate assessment contract; they must not be relabeled biography. Captain Basalt's meeting note describes a family's preference. Homeward Pumice's general sociability does not establish a granite-specific preference. Velvet Slate is RETURNED, which is ineligible under the AVAILABLE-only policy even though the stone is back at the shelter.

## Future run records

The separate [reference-answer assertion set](../reference-answer-assertions/README.md) calibrates a future semantic judge on observation coverage, negation, individual/type scope and mandatory conditions. It contains reviewed good/bad frozen answers whose citations can be structurally valid despite wrong meaning. It does not grade or mark these twenty scenarios as run. Keep structural binding, semantic assertions, retrieval coverage and final-answer completeness as separate results.

Do not reuse the quiet-home-specific six-model runner as if it already grades all these cases: its rubric and condition assertions are scenario-specific. A future runner must consume per-case expectations and distinguish reference responses from candidate assessments.

For each run, preserve suite and scenario IDs, question, fixture hashes, actual messages and DTO schema, all stage model selections, reasoning/token settings, response, per-stage checks, judge rubric/version, costs, failures and trace ID. Store runs separately; do not overwrite this specification or historical archives. Start with one approved model configuration over twenty cases before multiplying models. No paid call is triggered by reading or validating this manifest.
