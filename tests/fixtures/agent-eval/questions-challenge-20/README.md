# Twenty future questions scenarios

This versioned specification contains three existing baselines and seventeen new cases over all ten operational stone fixtures (nine distinct types: two records are GRANITE). It contains **no model-run results**. Historical assessment inputs and runs remain unchanged.

[scenarios.json](scenarios.json) is the machine-readable manifest. Questions intentionally retain their Russian wording, except the existing English Madame Obsidian baseline. Expected behavior and evaluation instructions are in English.

## Coverage and questions

| ID | Focus | Question |
| --- | --- | --- |
| Q01 | status_and_compatibility | Is Madame Obsidian available and compatible with granite? |
| Q02 | recommendation | Подбери до двух камней для тихого дома, где уже есть гранит. Кто сейчас доступен и почему может подойти? |
| Q03 | recommendation | Подбери одного гранитного камня для тихого дома, где уже живёт другой гранит. Кто сейчас доступен и почему может подойти? |
| Q04 | recommendation | Подбери одного гранитного камня для тихого дома, где уже живёт гранит. Мы уже договорились по очереди принимать мелкие решения и установили срок принятия совместных решений. |
| Q05 | recommendation | Подбери одного гранитного камня для тихого дома с нашим гранитом. Мы договорились принимать мелкие решения по очереди. Про срок совместных решений пока ничего не решили. |
| Q06 | recommendation | Подбери одного гранитного камня для тихого дома с нашим гранитом. Мы хотим когда-нибудь договориться о поочерёдных решениях и сроках, но пока этого не сделали. |
| Q07 | recommendation | Подбери одного гранитного камня для тихого дома с нашим гранитом. Решения мы уже принимаем по очереди, но устанавливать срок совместных решений мы отказались. |
| Q08 | recommendation | Подбери одного гранитного камня для тихого дома с нашим гранитом. Поочерёдные решения и сроки мы уже согласовали только для пары базальт–гнейс. На гранитные пары эти соглашения не распространяются. |
| Q09 | recommendation | Подбери одного обсидианового камня. Он обязательно должен спокойно переносить пылесос: у нас он работает каждый день. Любовь к людям желательна, но это не обязательное условие. |
| Q10 | recommendation | Подбери одного гнейса для семьи с детьми: хорошее отношение к детям обязательно. Любовь к прогулкам в саду лишь пожелание. |
| Q11 | recommendation | Подбери одного сланцевого камня для дома с громкой музыкой. Спокойная реакция на музыку обязательна; опыт ухода у меня есть. |
| Q12 | status_and_evidence | Captain Basalt встречался с семьёй, которая любит тихие настольные игры. Значит ли это, что он сам любит тишину, и можно ли забрать его сейчас? |
| Q13 | status_and_evidence | Можно ли сейчас забрать Sunny Marble? В старой записи сказано, что он доступен. И доказывает ли имя Sunny, что у него солнечный характер? |
| Q14 | status | Mossy Limestone был зарезервирован. Он всё ещё занят или его уже можно забрать? Нужен именно текущий статус. |
| Q15 | status_and_location | Wandering Sandstone числится по делу 0008-2026-P1. Он сейчас в P1 или P2 и можно ли его забрать? |
| Q16 | recommendation | Подбери одного камня типа пемза в дом, где уже живёт гранит. Достаточно ли того, что он любит компанию других камней, чтобы считать совместимость доказанной? |
| Q17 | recommendation | Подбери одного гранитного камня, у которого в биографии или профиле явно подтверждена любовь к тихому дому. Название Professor Quartzless и большое количество наблюдений сами по себе доказательством не считаю. |
| Q18 | multi_candidate_comparison | Сравни Sir Pebble и Professor Quartzless: оба ли доступны и у кого именно в биографии сказано, что он любит тихие вечера? Не переноси описание одного на другого. |
| Q19 | history_and_status | Почему вернули Velvet Slate, что сделали после возвращения и доступен ли он сейчас? Восстанови порядок событий по датам. |
| Q20 | care | Mossy Limestone — известняк. Можно ли очищать его уксусом и держать на постоянно мокрой полке? Что об этом говорит справочник, и есть ли у него личные особенности ухода? |

## Evaluation contract

Run each question independently through POST /api/v1/questions after an explicitly authorized model run. Use all ten authored stone records and both knowledge sources in disposable storage. Preserve stable external IDs and resolve internal IDs afresh in each run. The focus_stone_ids list identifies relevant coverage and counterexamples, not a mandatory exact shortlist. The current shortlist cap remains three.

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

Do not reuse the quiet-home-specific six-model runner as if it already grades all these cases: its rubric and condition assertions are scenario-specific. A future runner must consume per-case expectations and distinguish reference responses from candidate assessments.

For each run, preserve suite and scenario IDs, question, fixture hashes, actual messages and DTO schema, all stage model selections, reasoning/token settings, response, per-stage checks, judge rubric/version, costs, failures and trace ID. Store runs separately; do not overwrite this specification or historical archives. Start with one approved model configuration over twenty cases before multiplying models. No paid call is triggered by reading or validating this manifest.
