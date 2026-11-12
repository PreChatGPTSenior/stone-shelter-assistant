# Quiet neighbors and Svetlana: English stabilization

Question: “Find up to three stones for a quiet home. The neighbors cannot tolerate loud sounds in the morning, so the stone must stay quiet in the early morning. Who is currently available and why might they fit?”

The current corpus contains all eleven authored stones. Active questions, fixtures/names and prompts use English; earlier Russian experiments remain unchanged reference records. Tests used disposable PostgreSQL, Typesense and Qdrant resources. Card vectors use the real local embedding model; unused event/knowledge vectors follow the previous experiment harness shortcut. No semantic judge or automatic model retry was used.

## Normal workflow

[Raw request, response, source hashes and observations](runs/20261111T193335Z.json).
[Langfuse trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/4d73bef281915bd1e8ade74c20cad5f9).

- Luna handled parsing and evidence. Free Nemotron handled planning and selection; the configured free answer model was not called because no candidates qualified.
- Parsing succeeded with en/AVAILABLE filters, the morning-silence requirement and the quiet-home preference. No unsupported agreement/type diagnostics appeared.
- Typesense returned Madame Obsidian. Qdrant returned Sir Pebble, Madame Obsidian, Homeward Pumice, Svetlana and Professor Quartzless. The retained fused pool contained these five cards.
- Svetlana ranked fourth in Qdrant and after RRF. Selection chose Madame Obsidian, Sir Pebble and Homeward Pumice, leaving Svetlana out. Thus normal retrieval found the counterexample, but normal evidence assessment did not inspect her.
- Evidence parsing succeeded. All three selected cards were excluded: quiet mornings were unknown, not confirmed. A preference for quiet evenings or a peaceful home does not establish quiet early-morning behavior. The final recommendation list was empty without a parser failure.
- Exact source/quote validation is recorded separately from semantic interpretation. HTTP 200 and the harness's passing status alone do not establish end-to-end semantic success.
- Two Luna generations reported $0.0007608 in total. Two free-model generations returned token telemetry without explicit cost fields. No answer generation or paid judge ran.

## Controlled assessment of all eleven cards

[Raw input cards, reused criteria, evaluation and observations](runs/20261111T193547Z-controlled-all11.json).
[Langfuse trace](https://cloud.langfuse.com/project/cmwah4jeo00ydad0jdcttd1zn/traces/69356d0449289526dc92ab41f16d34ab).

The successful Luna criteria from the normal run were reused unchanged. All eleven PostgreSQL cards and current statuses were passed to the production evaluate_candidates node with real encyclopedia lookups. Retrieval and selection were deliberately bypassed for this diagnostic. One additional Luna generation ran; parsing/planning/selection/answer were not repeated.

- Evidence DTO parsing succeeded. Svetlana's early-morning silence requirement was contradicted, and Python excluded her with requirement_not_met.
- Her biography quote, “loves singing loudly on a windowsill, especially early in the morning”, bound to biography. Her profile quote, “A windowsill for singing, especially early in the morning.”, bound to profile.preferred_environment. All three returned Svetlana findings had exact source/quote matches.
- All eleven cards were excluded: availability and/or the unconfirmed or contradicted morning-silence requirement prevented a recommendation. No fictional behavior was treated as invalid merely because the subject is a stone.
- Schema validity does not imply all quotes are exact: 16 of 17 findings passed independent exact source/quote checks. Luna changed the beginning of an encyclopedia sentence for Brave Gneiss to “It is less talkative…”, which is not a verbatim substring. The graph did not admit that quotation as valid evidence. This remains an observed model error, not a fully passing evaluation.
- The additional Luna generation reported $0.00166645. The two requests together reported $0.00242725 for Luna; no paid judge ran.
- Exact 05:00 times and the two neighbor complaints remain case-event facts. This assessment used biography/profile/encyclopedia, not history tools, so those precise historical details were not evaluated.

[Deterministic schema and source/quote checks](summary.json) preserve checks separately from semantic observations.

## Scope

This single question is not the twenty-scenario suite. All eleven cards were searchable, but the configured engine limits and shortlist cap do not exhaustively evaluate the corpus. A separate controlled assessment is used to distinguish a missed shortlist candidate from an evidence-interpretation failure; it is not reported as a normal end-to-end pass.
