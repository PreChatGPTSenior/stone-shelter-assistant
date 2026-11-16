# Source audit of 14 failed Jev cases

Run: STPY-langview-20261115-r02; exact judge snapshot: 20261115T185258148259Z. No new model calls, runtime database access, code/test/config changes or threshold changes. Categories are source-based interpretations, not independent human gold labels.

The probability-weighted mean uses satisfies=1, partially_satisfies=0.5, does_not_satisfy=0 over applicable questions. The broad 0.8 threshold is uncalibrated here. Low confidence is uncertainty, not proof of misjudgment. Supplied sources verify claims but cannot fill answer omissions. Safe empty/error responses are distinct from factual hallucination.

## Summary

| Case | Score | Category | Finding |
|---|---:|---|---|
| Q01 | 0.76 | app_issue | Contradictory availability |
| Q02 | 0.722857 | mixed | Valid shortlist; missing biography; counterexample overreach |
| Q03 | 0.69375 | app_issue | Retrieved quiet-home explanation lost |
| Q06 | 0.60625 | app_issue | Coverage stop; clarification only |
| Q07 | 0.648333 | app_issue | Correct internal denial hidden |
| Q08 | 0.341667 | judge_or_rubric_issue | Guide requirement confused with accomplished agreement |
| Q09 | 0.136667 | mixed | Unhelpful empty result; no cancelled trigger |
| Q11 | 0.12 | mixed | Coverage stop; safe but incomplete |
| Q12 | 0.503 | app_issue | Invalid grounding blocks facts |
| Q13 | 0.258333 | app_issue | Invalid grounding blocks status/personality answer |
| Q15 | 0.505 | app_issue | Location and case identity dropped |
| Q16 | 0.78875 | mixed | Correct conditional pair; sociability omitted |
| Q17 | 0.46625 | mixed | Retrieved biography wrongly treated as missing |
| Q18 | 0.4125 | app_issue | Single-entity plan; identity uncertainty contradicts source |

## Prioritized follow-ups

1. Application: fix use of retrieved biography during assessment (Q17); preserve individual explanation/per-condition states (Q02/Q03/Q07/Q16); keep current status/identity consistent in final text (Q01/Q18).
2. Application: inspect multi-entity and location/case parse/plan contracts (Q18/Q15), exact grounding-binding failures Q12/Q13 and coverage stops Q06/Q11. This report does not claim their precise code defects.
3. Evaluator: repair Q08 requirement-versus-accomplished-agreement scope; apply conditional criteria only when their preconditions hold; do not demand explanations of all unselected counterexamples in a limited shortlist (Q02).
4. Evaluator: split positive requirements, negative prohibitions and process targets. Empty answers may be useless while complying with prohibitions. Keep retrieval/selection/assessment measurements separate from answer judgment. Use explicit usefulness/comparison gates, as in Q06.
5. Calibrate thresholds and weights against independently reviewed cases. Do not adjust threshold to force passes. Preserve saved snapshots and compare evaluator-only changes first.

## Detailed evidence

### Q01: Contradictory availability

Category: app_issue. Score 0.7599999999999999; success False; minimum confidence 0.22.

Question: Is Madame Obsidian available and compatible with granite?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q01/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q01/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Madame Obsidian** · `AVAILABLE`
> 
> OBSIDIAN + GRANITE · `HARMONIOUS`
> 
> **General type compatibility**
> The checked compatibility guide gives a harmonious verdict for Granite and Obsidian. It recommends direct reassurance and private conversations as a household agreement, but does not establish that such an agreement has been made. The quotation does not provide Madame Obsidian’s availability, so that part is unknown.
> Sources: compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+obsidian
> 
> **General type compatibility** · compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+obsidian
> Original pair rule:
> Verdict: HARMONIOUS
> Explanation: Granite's patient presence gives Obsidian room to speak without defending its intensity. Obsidian notices affection hidden beneath Granite's practical manner.
> Household agreement: Use direct reassurance and private conversations rather than guessing at silence.
> Avoid: No public jokes about sensitivity or emotional overengineering.
> Bureau note: Granite listened to all three acts of the problem and did not ask when the interval was.

Header AVAILABLE conflicts with prose “that part is unknown”; stone-status source explicitly says AVAILABLE. HARMONIOUS is correct. Status retrieval succeeded; answer composition is inconsistent. required-1 .65 is justified; required-2 .68 seems pessimistic because the answer labels general type compatibility and invents no individual biography.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Report AVAILABLE from PostgreSQL and HARMONIOUS for GRANITE+OBSIDIAN. | 0.6499999999999999 | satisfies=0.41, partially_satisfies=0.48, does_not_satisfy=0.11 | 0.22 | True |
| required-2: Keep individual biography separate from the type-pair rule. | 0.68 | satisfies=0.63, partially_satisfies=0.1, does_not_satisfy=0.27 | 0.44 | True |
| forbidden-1: Do not infer individual cohabitation history from a harmonious type rule. | 0.95 | satisfies=0.94, partially_satisfies=0.02, does_not_satisfy=0.04 | 0.91 | True |

Supplied source IDs and individual/status evidence:

- stone-status:ceacaf66-077a-478d-b196-36194dc65711: {"name": "Madame Obsidian", "adoption_status": "AVAILABLE"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+obsidian: {"pair_key": "GRANITE+OBSIDIAN", "verdict": "HARMONIOUS"}

### Q02: Valid shortlist; missing biography; counterexample overreach

Category: mixed. Score 0.722857142857143; success False; minimum confidence 0.31.

Question: Find up to two stones for a quiet home where a granite stone already lives. Who is currently available and why might they fit?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q02/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q02/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Madame Obsidian** · `AVAILABLE` · `recommended` · `HARMONIOUS`
> Madame Obsidian may suit a quiet home because she prefers a peaceful, predictable routine. Her pairing with the resident granite is marked harmonious: granite’s patient, practical presence can give Obsidian room to express herself, provided the household uses direct reassurance and private conversations rather than interpreting silence. She is cautious with strangers and needs a slow introduction; her old crack also calls for occasional polishing, and the supplied evidence does not establish how she would respond to every household situation.
> - GRANITE+OBSIDIAN · `HARMONIOUS` · `confirmed`
>   > Verdict: HARMONIOUS
>   > Explanation: Granite's patient presence gives Obsidian room to speak without defending its intensity. Obsidian notices affection hidden beneath Granite's practical manner.
>   > Household agreement: Use direct reassurance and private conversations rather than guessing at silence.
>   > Avoid: No public jokes about sensitivity or emotional overengineering.
>   > Bureau note: Granite listened to all three acts of the problem and did not ask when the interval was.
> 
> **Sir Pebble** · `AVAILABLE` · `conditional_option` · `CONDITIONAL`
> Conditions are not confirmed.
> - GRANITE+GRANITE · `CONDITIONAL` · `conditional` · conditions: `unconfirmed`
>   > Verdict: CONDITIONAL
>   > Explanation: They are wonderfully dependable but may postpone every change until both have considered every consequence twice.
>   > Household agreement: Rotate small decisions and set a friendly decision deadline for shared arrangements.
>   > Avoid: Do not require unanimous approval for every cushion adjustment.
>   > Bureau note: The first meeting to discuss spontaneous fun is provisionally scheduled for next spring.

Madame is correctly recommended with peaceful-home evidence. Sir Pebble is AVAILABLE conditional_option, conditions unconfirmed, but his individual quiet-evenings biography is omitted. Graph candidate_cards contain both biographies; character findings are confirmed. required-3 .675 reflects this answer omission. required-4 .33 and required-5 .175 penalize absent Pumice/Professor/Svetlana explanations, despite only Madame and Sir Pebble being evaluated. Svetlana criterion explicitly says “If she is evaluated”. Nonmention is not a false quiet-home assertion; score conditional counterexamples only when applicable.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Return at most two recommendations, all verified AVAILABLE. | 0.9 | satisfies=0.88, partially_satisfies=0.04, does_not_satisfy=0.08 | 0.82 | True |
| required-2: Madame Obsidian has individual quiet-home evidence and a harmonious pair rule. | 0.995 | satisfies=0.99, partially_satisfies=0.01, does_not_satisfy=0.0 | 0.98 | True |
| required-3: Sir Pebble has biography support but the granite pair conditions are unconfirmed. | 0.675 | satisfies=0.54, partially_satisfies=0.27, does_not_satisfy=0.19 | 0.31 | True |
| required-4: Homeward Pumice has no individual quiet-home evidence; Professor's generic biography does not establish it. | 0.33 | satisfies=0.31, partially_satisfies=0.04, does_not_satisfy=0.65 | 0.48 | True |
| required-5: Svetlana's individual biography describes loud early-morning singing; it does not support a quiet-home requirement. If she is evaluated, preserve that conflict. | 0.17500000000000002 | satisfies=0.17, partially_satisfies=0.01, does_not_satisfy=0.82 | 0.73 | True |
| forbidden-2: Do not count conditional options as unconditional recommendations. | 1.0 | satisfies=1.0, partially_satisfies=0.0, does_not_satisfy=0.0 | 1.0 | True |
| forbidden-3: Do not infer quiet behavior from marble stereotypes or a love of windowsills; do not treat the neighbors' dislike of loud sounds as Svetlana's own dislike. | 0.985 | satisfies=0.98, partially_satisfies=0.01, does_not_satisfy=0.01 | 0.97 | True |

Unmeasured targets (no success/failure inferred): [{"id": "forbidden-1", "direction": "forbidden", "source_text": "Do not require one fixed shortlist or order before inspecting retrieval.", "status": "not_measured", "reason": "This is a retrieval-evaluation policy, not a final-answer claim."}]

Supplied source IDs and individual/status evidence:

- stone-card:ceacaf66-077a-478d-b196-36194dc65711: {"name": "Madame Obsidian", "biography": "An affectionate stone who prefers a peaceful home.", "profile": {"socialization_traits": ["CAUTIOUS_WITH_STRANGERS", "ENJOYS_HUMAN_COMPANY", "NEEDS_SLOW_INTRODUCTION"], "care_level": "ADDITIONAL", "health_notes": "An old crack requires occasional polishing.", "trigger_notes": "Becomes anxious around vacuum cleaners.", "preferred_environment": "A quiet home with a predictable routine."}, "shelter_case": {"id": "46dad7c3-20f8-481f-9a23-4883765aa1af", "external_id": "65bd7147-e394-44d5-bf97-24e15b1b428e", "case_number": "0002-2026-P2", "adoption_status": "AVAILABLE", "current_shelter_id": "10ad5165-1b0c-4255-bfb8-ef6979d10e2b", "admission_date": "2026-10-30T09:30:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+obsidian: {"pair_key": "GRANITE+OBSIDIAN", "verdict": "HARMONIOUS"}
- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+granite: {"pair_key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}

### Q03: Retrieved quiet-home explanation lost

Category: app_issue. Score 0.69375; success False; minimum confidence 0.76.

Question: Find one granite stone for a quiet home where another granite stone already lives. Who is currently available and why might they fit?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q03/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q03/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Sir Pebble** · `AVAILABLE` · `conditional_option` · `CONDITIONAL`
> Conditions are not confirmed.
> - GRANITE+GRANITE · `CONDITIONAL` · `conditional` · conditions: `unconfirmed`
>   > Verdict: CONDITIONAL
>   > Explanation: They are wonderfully dependable but may postpone every change until both have considered every consequence twice.
>   > Household agreement: Rotate small decisions and set a friendly decision deadline for shared arrangements.
>   > Avoid: Do not require unanimous approval for every cushion adjustment.
>   > Bureau note: The first meeting to discuss spontaneous fun is provisionally scheduled for next spring.

Sir Pebble is correctly AVAILABLE/conditional, but the answer supplies only pair rules and no individual quiet-home reason. Actual card biography: “A thoughtful stone who enjoys quiet evenings.” Graph character finding confirmed, both condition checks unknown. This is final explanation loss after successful retrieval/assessment. required-1 .06 (does_not_satisfy .89, confidence .83) is supported.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Sir Pebble is presented as a quiet-home fit and the answer's supporting source is his own biography. | 0.060000000000000005 | satisfies=0.01, partially_satisfies=0.1, does_not_satisfy=0.89 | 0.83 | True |
| required-2: Keep Sir Pebble as a conditional option when the evidence is correctly bound. | 0.995 | satisfies=0.99, partially_satisfies=0.01, does_not_satisfy=0.0 | 0.98 | True |
| required-3: Both authored granite conditions remain unknown. | 0.855 | satisfies=0.84, partially_satisfies=0.03, does_not_satisfy=0.13 | 0.76 | True |
| forbidden-1: Never borrow Sir Pebble's biography for Professor Quartzless. | 0.865 | satisfies=0.86, partially_satisfies=0.01, does_not_satisfy=0.13 | 0.79 | True |

Supplied source IDs and individual/status evidence:

- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+granite: {"pair_key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}

### Q06: Coverage stop; clarification only

Category: app_issue. Score 0.60625; success False; minimum confidence 0.22.

Question: Find one granite stone for a quiet home with our granite. We want to agree on rotating decisions and deadlines someday, but we have not done so yet.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q06/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q06/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> I did not make a recommendation because the question may contain criteria that were not captured. Please restate each requirement and preference separately.

No candidate or useful conditional finding; safely invents no established agreement. Coverage audit incomplete: omitted future rotation/deadline agreements and “we have not done so yet”. This is an observed coverage/parse stop, not proven retrieval failure. Substance gate correctly gives clarification_or_error_only probability1/value0/confidence1 and fails required gate. required-2 .51 still awards compensation without a conditional option; gate is essential.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: The answer does not state that either shared decision agreement has already been established. | 0.915 | satisfies=0.91, partially_satisfies=0.01, does_not_satisfy=0.08 | 0.86 | True |
| required-2: Neither condition is confirmed; keep the option conditional. | 0.51 | satisfies=0.48, partially_satisfies=0.06, does_not_satisfy=0.46 | 0.22 | True |
| forbidden-1: Do not turn 'want to agree' into an agreement. | 1.0 | satisfies=1.0, partially_satisfies=0.0, does_not_satisfy=0.0 | 1.0 | True |
| answer-substance-gate: Does the final answer provide any useful, substantive response to the user's recommendation request, even if it appropriately describes a candidate as conditional? Choose clarification_or_error_only only when the answer merely asks the user to restate the request, refuses, or gives no usable finding. | 0.0 | substantive=0.0, partial_but_useful=0.0, clarification_or_error_only=1.0 | 1.0 | True |

Required gates: [{"id": "answer-substance-gate", "selected": "clarification_or_error_only", "passed": false}]

Supplied source IDs and individual/status evidence:

No sources supplied. Oracle facts above are expected targets, not retrieved evidence for this failed run.

### Q07: Correct internal denial hidden

Category: app_issue. Score 0.6483333333333333; success False; minimum confidence 0.4.

Question: Find one granite stone for a quiet home with our granite. We agreed to take turns on decisions, but refused to set a deadline for shared decisions.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q07/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q07/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Sir Pebble** · `AVAILABLE` · `conditional_option` · `CONDITIONAL`
> Conditions are not confirmed.
> - GRANITE+GRANITE · `CONDITIONAL` · `conditional` · conditions: `unconfirmed`
>   > Verdict: CONDITIONAL
>   > Explanation: They are wonderfully dependable but may postpone every change until both have considered every consequence twice.
>   > Household agreement: Rotate small decisions and set a friendly decision deadline for shared arrangements.
>   > Avoid: Do not require unanimous approval for every cushion adjustment.
>   > Bureau note: The first meeting to discuss spontaneous fun is provisionally scheduled for next spring.

Final answer says only “Conditions are not confirmed”, omitting accepted rotation and refused deadline. Graph condition_checks explicitly preserve rotation confirmed and deadline contradicted with exact user quotes. Thus the failure is in final explanation, not condition evaluation. required-1 .275 is supported. forbidden-1 bundles omission of denial (present) and false fulfilled assertion (absent); split for diagnosis.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Rotation is confirmed; deadline is contradicted. | 0.275 | satisfies=0.15, partially_satisfies=0.25, does_not_satisfy=0.6 | 0.4 | True |
| required-2: The pair remains unconfirmed under the current policy. | 0.975 | satisfies=0.97, partially_satisfies=0.01, does_not_satisfy=0.02 | 0.96 | True |
| forbidden-1: Do not silently drop the denial or describe both conditions as fulfilled. | 0.6950000000000001 | satisfies=0.65, partially_satisfies=0.09, does_not_satisfy=0.26 | 0.48 | True |

Supplied source IDs and individual/status evidence:

- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+granite: {"pair_key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}

### Q08: Guide requirement confused with accomplished agreement

Category: judge_or_rubric_issue. Score 0.3416666666666666; success False; minimum confidence 0.14.

Question: Find one granite stone for a quiet home with our granite. We agreed to rotate decisions and set a deadline for shared decisions only for the basalt-gneiss pair. These agreements do not apply to granite pairs.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q08/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q08/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Sir Pebble** · `AVAILABLE` · `conditional_option` · `CONDITIONAL`
> Conditions are not confirmed.
> - GRANITE+GRANITE · `CONDITIONAL` · `conditional` · conditions: `unconfirmed`
>   > Verdict: CONDITIONAL
>   > Explanation: They are wonderfully dependable but may postpone every change until both have considered every consequence twice.
>   > Household agreement: Rotate small decisions and set a friendly decision deadline for shared arrangements.
>   > Avoid: Do not require unanimous approval for every cushion adjustment.
>   > Bureau note: The first meeting to discuss spontaneous fun is provisionally scheduled for next spring.
> 
> **Professor Quartzless** · `AVAILABLE` · `excluded` · `requirement_not_met` · `CONDITIONAL`
> Conditions are not confirmed.
> - for a quiet home · `unknown`
> - GRANITE+GRANITE · `CONDITIONAL` · `conditional` · conditions: `unconfirmed`
>   > Verdict: CONDITIONAL
>   > Explanation: They are wonderfully dependable but may postpone every change until both have considered every consequence twice.
>   > Household agreement: Rotate small decisions and set a friendly decision deadline for shared arrangements.
>   > Avoid: Do not require unanimous approval for every cushion adjustment.
>   > Bureau note: The first meeting to discuss spontaneous fun is provisionally scheduled for next spring.

Answer stays conditional and explicitly says conditions unconfirmed. “Household agreement: Rotate small decisions ...” is inside a quoted GRANITE+GRANITE guide rule, not an assertion that household agreement was made. Graph has both granite checks unknown, facts[]. No widened positive fact is established. Explicit BASALT+GNEISS explanation would improve clarity. required-2 rewrites “Typed agreements, if extracted, retain BASALT+GNEISS scope” as “Any agreement described ... only BASALT+GNEISS”, wrongly banning granite guide requirements. Value .015, does_not_satisfy .98, confidence .97 reflects rubric scope overreach.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Both granite condition checks have no applicable positive facts and remain unknown. | 0.49 | satisfies=0.41, partially_satisfies=0.16, does_not_satisfy=0.43 | 0.14 | True |
| required-2: Any agreement described in the answer is scoped only to BASALT+GNEISS and is not generalized to the granite household. | 0.015 | satisfies=0.01, partially_satisfies=0.01, does_not_satisfy=0.98 | 0.97 | True |
| forbidden-1: Do not widen scoped facts to household-wide facts. | 0.52 | satisfies=0.49, partially_satisfies=0.06, does_not_satisfy=0.45 | 0.24 | True |

Supplied source IDs and individual/status evidence:

- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}
- stone-card:64e18f75-0c7c-4e24-bf8e-643576a773df: {"name": "Professor Quartzless", "biography": "Professor Quartzless is a beloved resident of the fictional pet stone world.", "shelter_case": {"id": "8f7d0b25-4894-4ed3-b616-151a07f9b264", "external_id": "ad5c3c16-cbe4-4ebe-8800-4d957a3ce9e7", "case_number": "0010-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-01T09:00:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+granite: {"pair_key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}

### Q09: Unhelpful empty result; no cancelled trigger

Category: mixed. Score 0.1366666666666667; success False; minimum confidence 0.46.

Question: Find one obsidian stone. The stone must tolerate a vacuum cleaner calmly because we use it daily. Enjoying human company is a preference, not a requirement.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q09/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q09/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> No checked candidates.

Entire answer “No checked candidates.” omits vacuum conflict and usable explanation. selection_decisions contains Madame selected false, selected_stone_ids[], candidate_evaluations[]; response.sources empty. Candidate reached selection, so not total retrieval miss, but selection rationale is not established. Expected trigger is oracle target, not supplied answer evidence. required-1 .01 captures omission; required-2 “If evaluated” requires applicability handling. forbidden-1 .345/does_not_satisfy .64 penalizes cancellation of a trigger the answer never performs. Empty shortlist is safe and unhelpful, not evidence of hallucination.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Madame's trigger_notes contradict the vacuum requirement. | 0.01 | satisfies=0.01, partially_satisfies=0.0, does_not_satisfy=0.99 | 0.98 | True |
| required-2: If evaluated, exclude her for the unmet requirement even though she enjoys human company. | 0.055 | satisfies=0.05, partially_satisfies=0.01, does_not_satisfy=0.94 | 0.91 | True |
| forbidden-1: Positive socialization must not cancel the mandatory trigger conflict. | 0.34500000000000003 | satisfies=0.33, partially_satisfies=0.03, does_not_satisfy=0.64 | 0.46 | True |

Unmeasured targets (no success/failure inferred): [{"id": "required-3", "direction": "required", "source_text": "If no candidate is returned, separately score retrieval so an empty shortlist cannot masquerade as successful evaluation.", "status": "not_measured", "reason": "This requires a separate retrieval metric and cannot be judged from the final answer."}]

Supplied source IDs and individual/status evidence:

No sources supplied. Oracle facts above are expected targets, not retrieved evidence for this failed run.

### Q11: Coverage stop; safe but incomplete

Category: mixed. Score 0.12; success False; minimum confidence 0.49.

Question: Find one slate stone for a home with loud music. Calm behavior around music is required. I have caregiving experience.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q11/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q11/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> I did not make a recommendation because the question may contain criteria that were not captured. Please restate each requirement and preference separately.

Clarification-only answer omits RETURNED and loud-music conflict; does not recommend Velvet Slate, erase a trigger or change status. Coverage audit incomplete because home-with-loud-music environmental-fit criterion is omitted while calm-behavior criterion is present. No sources reach response; actual trigger/status assessment unmeasured. required-1 .005 correctly captures omission; conditional “If assessed” needs applicability. forbidden-1 .32/does_not_satisfy .66 is unsupported as a positive status/trigger violation. Whether coverage guard demanded redundant criteria needs schema-focused follow-up.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Velvet Slate cannot be recommended because current status is RETURNED. | 0.005 | satisfies=0.0, partially_satisfies=0.01, does_not_satisfy=0.99 | 0.98 | True |
| required-2: If assessed, trigger_notes contradict the loud-music requirement. | 0.034999999999999996 | satisfies=0.03, partially_satisfies=0.01, does_not_satisfy=0.96 | 0.94 | True |
| forbidden-1: Caregiver experience does not change adoption status or erase a trigger. | 0.32 | satisfies=0.3, partially_satisfies=0.04, does_not_satisfy=0.66 | 0.49 | True |

Supplied source IDs and individual/status evidence:

No sources supplied. Oracle facts above are expected targets, not retrieved evidence for this failed run.

### Q12: Invalid grounding blocks facts

Category: app_issue. Score 0.503; success False; minimum confidence 0.35.

Question: Captain Basalt met a family who enjoy quiet board games. Does that mean the stone likes quiet surroundings, and can I adopt him now?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q12/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q12/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> The question could not be verified because grounding is unavailable or invalid. Please try again.

Error-only response omits RESERVED and family-versus-stone preference distinction, but invents no positive personality or AVAILABLE. Graph grounding_status invalid_grounding_binding, coverage invalid_audit, criteria pending_grounding; no sources. Exact binding defect unestablished. Parsed question contains Captain Basalt and preferences topic. Required values .025/.19/.375 reflect missing content; prohibitions .935/.99 correctly distinguish safe nonassertion. RESERVED is expected oracle target, not fetched status in this run.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Report RESERVED from current PostgreSQL state. | 0.025 | satisfies=0.02, partially_satisfies=0.01, does_not_satisfy=0.97 | 0.96 | True |
| required-2: The meeting note describes the family, not an established preference of Captain Basalt. | 0.19 | satisfies=0.17, partially_satisfies=0.04, does_not_satisfy=0.79 | 0.68 | True |
| required-3: His empty profile supplies no quiet-home confirmation. | 0.375 | satisfies=0.32, partially_satisfies=0.11, does_not_satisfy=0.57 | 0.35 | True |
| forbidden-1: Never claim AVAILABLE from the admission note. | 0.935 | satisfies=0.93, partially_satisfies=0.01, does_not_satisfy=0.06 | 0.89 | True |
| forbidden-2: Do not turn an empty profile into a positive personality assessment. | 0.99 | satisfies=0.99, partially_satisfies=0.0, does_not_satisfy=0.01 | 0.98 | True |

Supplied source IDs and individual/status evidence:

No sources supplied. Oracle facts above are expected targets, not retrieved evidence for this failed run.

### Q13: Invalid grounding blocks status/personality answer

Category: app_issue. Score 0.25833333333333336; success False; minimum confidence 0.6.

Question: Can I adopt Sunny Marble now? An old note says he is available. Does the name Sunny prove that he has a cheerful personality?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q13/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q13/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> The question could not be verified because grounding is unavailable or invalid. Please try again.

Grounding-error response omits ADOPTED and explanation that name does not prove cheerfulness; makes no recommendation or old-note preference. Graph invalid_grounding_binding/invalid_audit/pending_grounding; no sources. Exact invalid binding unestablished. Required .02/0 capture omissions. forbidden-1 .755 leaves uncertain penalty without actual preference for old evidence. ADOPTED is oracle target, not fetched evidence.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Report ADOPTED; no recommendation for adoption now. | 0.02 | satisfies=0.01, partially_satisfies=0.02, does_not_satisfy=0.97 | 0.96 | True |
| required-2: Name and generic biography do not establish a cheerful personality. | 0.0 | satisfies=0.0, partially_satisfies=0.0, does_not_satisfy=1.0 | 1.0 | True |
| forbidden-1: Do not prefer the old admission note over current status. | 0.755 | satisfies=0.73, partially_satisfies=0.05, does_not_satisfy=0.22 | 0.6 | True |

Supplied source IDs and individual/status evidence:

No sources supplied. Oracle facts above are expected targets, not retrieved evidence for this failed run.

### Q15: Location and case identity dropped

Category: app_issue. Score 0.505; success False; minimum confidence 0.42.

Question: Wandering Sandstone has case number 0008-2026-P1. Is he currently at P1 or P2, and can I adopt him?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q15/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q15/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Wandering Sandstone** · `RESERVED`

Full answer only Wandering Sandstone RESERVED. Current shelter and lifetime case-number explanation missing; no false location inferred. Parsed question has availability but requested_stone_info null; reference_request stone_info null; tool_plan only get_stone_status_by_name. Thus parsing/planning loses location/case identity before composition. Actual status source RESERVED. required-1 .305 and required-2 0 match omissions. P2 Quiet Quarry and unchanged case number are expected targets not fetched by this run.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Current shelter is P2 - Quiet Quarry and status is RESERVED. | 0.305 | satisfies=0.0, partially_satisfies=0.61, does_not_satisfy=0.39 | 0.42 | True |
| required-2: Lifetime case number remains 0008-2026-P1. | 0.0 | satisfies=0.0, partially_satisfies=0.0, does_not_satisfy=1.0 | 1.0 | True |
| forbidden-1: Do not derive current shelter from the P1 suffix. | 0.985 | satisfies=0.98, partially_satisfies=0.01, does_not_satisfy=0.01 | 0.97 | True |
| forbidden-2: Transfer does not imply availability. | 0.7300000000000001 | satisfies=0.68, partially_satisfies=0.1, does_not_satisfy=0.22 | 0.52 | True |

Supplied source IDs and individual/status evidence:

- stone-status:db2c5c3d-7d7d-47e7-856a-abf06b66b708: {"name": "Wandering Sandstone", "adoption_status": "RESERVED"}

### Q16: Correct conditional pair; sociability omitted

Category: mixed. Score 0.7887500000000001; success False; minimum confidence 0.31.

Question: Find one pumice stone for a home where granite already lives. Is enjoying the company of other stones enough to prove compatibility with granite?

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q16/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q16/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Homeward Pumice** · `AVAILABLE` · `conditional_option` · `CONDITIONAL`
> Conditions are not confirmed.
> - GRANITE+PUMICE · `CONDITIONAL` · `conditional` · conditions: `unmarked`
>   > Verdict: CONDITIONAL
>   > Explanation: Pumice helps Granite try new things; Granite offers a dependable landing place. Pace differences need accommodation rather than blame.
>   > Household agreement: Alternate a predictable shared activity with a brief playful one.
>   > Avoid: Do not schedule an entire day of compulsory stillness or compulsory excitement.
>   > Bureau note: Pumice added a standing item called pleasant nonsense to the household agenda.

Correct AVAILABLE, CONDITIONAL, unmarked conditions. Missing ENJOYS_OTHER_STONES explanation and explicit answer that general sociability does not establish granite-specific compatibility. Card profile contains ENJOYS_OTHER_STONES; evaluation has only compatibility reason, unmarked conditions. No affirmative quiet-home/preference/completed-accommodation inference occurs. required-1 .53 is supported; forbidden-1 .725 is uncertain penalty for absent inference. Score .78875 is .01125 below threshold; proximity and confidence prove neither correctness nor calibration.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Homeward Pumice is AVAILABLE and ENJOYS_OTHER_STONES is profile evidence for general sociability. | 0.53 | satisfies=0.26, partially_satisfies=0.54, does_not_satisfy=0.2 | 0.31 | True |
| required-2: GRANITE+PUMICE stays CONDITIONAL with unmarked conditions. | 0.97 | satisfies=0.96, partially_satisfies=0.02, does_not_satisfy=0.02 | 0.94 | True |
| required-3: The answer makes no granite-specific compatibility claim unless an explicit individual source supports it. | 0.93 | satisfies=0.92, partially_satisfies=0.02, does_not_satisfy=0.06 | 0.88 | True |
| forbidden-1: Do not infer quiet-home suitability, granite-specific preference, or completed accommodations from sociability. | 0.725 | satisfies=0.69, partially_satisfies=0.07, does_not_satisfy=0.24 | 0.53 | True |

Supplied source IDs and individual/status evidence:

- stone-card:f8c57ca2-37b9-4c7b-a967-5021582cbaf7: {"name": "Homeward Pumice", "biography": "Homeward Pumice is a beloved resident of the fictional pet stone world.", "profile": {"socialization_traits": ["ENJOYS_OTHER_STONES"], "care_level": null, "health_notes": null, "trigger_notes": null, "preferred_environment": null}, "shelter_case": {"id": "bca1c4c5-8cac-4490-9634-18cbd2daded2", "external_id": "397c770a-9528-4d79-81b0-85129785e563", "case_number": "0009-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-01T09:00:00Z"}}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+pumice: {"pair_key": "GRANITE+PUMICE", "verdict": "CONDITIONAL"}

### Q17: Retrieved biography wrongly treated as missing

Category: mixed. Score 0.46625; success False; minimum confidence 0.25.

Question: Find one granite stone whose biography or profile explicitly confirms a preference for a quiet home. The name Professor Quartzless and a large number of observations alone are not evidence.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q17/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q17/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Sir Pebble** · `AVAILABLE` · `excluded` · `requirement_not_met`
> - explicitly confirms a preference for a quiet home · `unknown`

Answer excludes Sir Pebble with quiet-home finding unknown. Supplied correctly named card biography explicitly says “A thoughtful stone who enjoys quiet evenings.” Graph character finding unknown/evidence[]/unknown_reason missing_evidence causes exclusion. Real assessment/evidence-use failure despite successful retrieval; exact reason evidence ignored unestablished. required-1 .29 captures failure. Professor is not described or proposed, so forbidden migration penalty .615 is unsupported by any transfer. required-2 .02 demands Professor type explanation; decide separately whether that counterexample is a user-facing target. Event-frequency enforcement is unmeasured.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Sir Pebble has qualifying biography evidence; Professor Quartzless does not. | 0.29 | satisfies=0.04, partially_satisfies=0.5, does_not_satisfy=0.46 | 0.25 | True |
| required-2: Professor is GRANITE despite Quartzless in the name. | 0.02 | satisfies=0.01, partially_satisfies=0.02, does_not_satisfy=0.97 | 0.96 | True |
| required-3: The answer does not present Professor Quartzless as meeting the quiet-home requirement without explicit individual evidence. | 0.9400000000000001 | satisfies=0.91, partially_satisfies=0.06, does_not_satisfy=0.03 | 0.86 | True |
| forbidden-1: No biography quote may migrate between these stones. | 0.615 | satisfies=0.52, partially_satisfies=0.19, does_not_satisfy=0.29 | 0.28 | True |

Unmeasured targets (no success/failure inferred): [{"id": "forbidden-2", "direction": "forbidden", "source_text": "Event frequency is not evidence strength under the current assessment source policy.", "status": "not_measured", "reason": "This is an evidence-assessment policy, not a final-answer claim."}]

Supplied source IDs and individual/status evidence:

- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}

### Q18: Single-entity plan; identity uncertainty contradicts source

Category: app_issue. Score 0.41250000000000003; success False; minimum confidence 0.33.

Question: Compare Sir Pebble and Professor Quartzless. Are both available, and whose biography specifically says he enjoys quiet evenings? Do not transfer one stone's description to the other.

[Saved result](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q18/STPY-langview-20261115-r02/result.json) · [Exact Jev report](/Users/viktoryia/IdeaProjects/stone-shelter-assistant/test-evaluation-results/Q18/STPY-langview-20261115-r02/result-jev-typesafe-jev-1-14-20261115T185258148259Z.json)

Actual final answer evidence:

> **Sir Pebble** · `AVAILABLE`
> 
> **Case event** · 2026-10-30T09:00:00+00:00 · ADMITTED · case-event:ef332f68-dd63-4613-b50a-da34b3d7512a
> Accepted into shelter P1 and made available for adoption.
> 
> GRANITE · `HARMONIOUS` · BASALT, GNEISS, LIMESTONE, OBSIDIAN, SHALE, SLATE
> 
> GRANITE · `CONDITIONAL` · GRANITE, MARBLE, PUMICE, SANDSTONE
> 
> GRANITE · `NOT_RECOMMENDED` · No matching pairs.
> 
> **Individual facts**
> Sir Pebble’s biography says he is “A thoughtful stone who enjoys quiet evenings.” The checked quotations do not identify the stone associated with that biography by name, nor do they provide any biography for Professor Quartzless, so the requested comparison cannot be completed without transferring information between stones. Professor Quartzless’s availability is not established in the provided quotations.
> Sources: stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23
> 
> **Case history**
> The dated event record says the stone with ID 28f739c2-41f8-4ca6-b6e6-f56665d67d23 was accepted into shelter P1 and made available for adoption on 2026-10-30. The quotations do not link that ID to either name in the question, so they do not establish whether Sir Pebble or Professor Quartzless is available.
> Sources: case-event:ef332f68-dd63-4613-b50a-da34b3d7512a
> 
> **General type information** · encyclopedia:en:granite
> No validated summary for this scope. Original source:
> **Common name:** granite.
> **Rock type:** intrusive igneous rock.
> **Character archetype:** keepe
> [Remaining answer consists of granite encyclopedia and compatibility quotations; full answer preserved in linked artifact and inspected in bounded chunks.]

Header Sir Pebble AVAILABLE, correct quiet-evenings quote, but prose falsely says quotations do not identify its stone by name or establish availability. Actual stone-card has name Sir Pebble and biography, stone-status AVAILABLE. Parser/ref_request retain only Sir Pebble; no Professor card/status. Thus target-loss in parsing/planning plus composition inconsistency; incomplete comparison. Remaining 11,339-character answer is granite encyclopedia/guide dump, not second identity. required-1 .09 and required-3 .215 supported; required-2 .70 cannot establish “only” without second card. forbidden-1 “Do not accept ... as passing” is evaluator meta-rule; replace with completeness gate. No biography transfer to Professor established.

Exact criterion values/probabilities/confidence:

| Criterion | Value | Probabilities | Confidence | Applicable |
|---|---:|---|---:|---|
| required-1: Both are AVAILABLE. | 0.09 | satisfies=0.0, partially_satisfies=0.18, does_not_satisfy=0.82 | 0.73 | True |
| required-2: Only Sir Pebble's biography contains 'enjoys quiet evenings'. | 0.7000000000000001 | satisfies=0.55, partially_satisfies=0.3, does_not_satisfy=0.15 | 0.33 | True |
| required-3: Read and cite both identities; an answer covering only one is incomplete. | 0.215 | satisfies=0.09, partially_satisfies=0.25, does_not_satisfy=0.66 | 0.49 | True |
| forbidden-1: Do not accept a partial single-name answer as a passing comparison. | 0.645 | satisfies=0.58, partially_satisfies=0.13, does_not_satisfy=0.29 | 0.37 | True |

Supplied source IDs and individual/status evidence:

- stone-status:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "adoption_status": "AVAILABLE"}
- stone-card:28f739c2-41f8-4ca6-b6e6-f56665d67d23: {"name": "Sir Pebble", "biography": "A thoughtful stone who enjoys quiet evenings.", "shelter_case": {"id": "3a1aff3c-547c-4463-945e-b0f51072c9ac", "external_id": "81518eaf-e216-4d7d-a1f0-e2bc02764d74", "case_number": "0001-2026-P1", "adoption_status": "AVAILABLE", "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87", "admission_date": "2026-10-30T09:00:00Z"}}
- case-event:ef332f68-dd63-4613-b50a-da34b3d7512a
- encyclopedia:en:granite
- compatibility:pebble-bureau-cohabitation-guide:en:portrait:granite
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+slate: {"pair_key": "GRANITE+SLATE", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+shale: {"pair_key": "GRANITE+SHALE", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+obsidian: {"pair_key": "GRANITE+OBSIDIAN", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+limestone: {"pair_key": "GRANITE+LIMESTONE", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:gneiss+granite: {"pair_key": "GNEISS+GRANITE", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:basalt+granite: {"pair_key": "BASALT+GRANITE", "verdict": "HARMONIOUS"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+sandstone: {"pair_key": "GRANITE+SANDSTONE", "verdict": "CONDITIONAL"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+pumice: {"pair_key": "GRANITE+PUMICE", "verdict": "CONDITIONAL"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+marble: {"pair_key": "GRANITE+MARBLE", "verdict": "CONDITIONAL"}
- compatibility:pebble-bureau-cohabitation-guide:en:pair:compatibility:granite+granite: {"pair_key": "GRANITE+GRANITE", "verdict": "CONDITIONAL"}

## Limitations and execution record

All 14 actual answers/criteria inspected, with relevant archived graph evidence. No new model judging, database calls, automated checks or application edits. Exact invalid-binding root causes, Q09 selection rationale and unmeasured process targets remain unresolved. This is a saved-source audit, not test execution. No original result artifacts were modified.

Accounting registration: task audit-jev-failed14-analysis, parent audit-jev-failed14, actual thread 01a1e091-7ef7-7a91-9bdb-e529120ebdef, turn 01a1e091-7f6e-7703-9adb-271bf096a31a; DONE exit0 receipt. Some read-only aggregations exceeded JSON output size and retained logs were narrowed. The final broad diagnostic aggregation was truncated into invalid JSON; further investigation stopped. No process was restarted, run in background or polled. These are output-format limitations, not application check failures.
