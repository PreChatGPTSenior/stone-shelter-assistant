# ADR: Hybrid stone retrieval with RRF

Status: Implementation and local validation complete. Paid-model quality comparison remains pending explicit authorization.
Task: PY-037, branch `PY-037-improve-search-continued`.
Scope: Candidate stone cards for recommendations through `POST /api/v1/questions`.

## Context and objective

Typesense and Qdrant currently return separate ranked lists of cards. The graph collects their results by ID, retaining the first card, then asks an LLM to select at most three candidates. It does not calculate a shared retrieval ranking or preserve per-engine contributions in the candidate pool.

Improve candidate recall and make inclusion explainable. A retrieval score determines which cards deserve assessment. PostgreSQL status, quoted evidence and the existing ranking policy determine whether a stone can be recommended.

## 1. One hybrid retrieval operation

Add `search_stones_hybrid` backed by `StoneSearchService`. For general recommendations, execute one hybrid operation per request before candidate selection. Run lexical and semantic retrieval concurrently with the same exact filters. Keep the existing individual methods for comparisons and exact-name retrieval.

Input:
- `lexical_query`: nonempty keyword query in the indexed text language.
- `semantic_query`: nonempty description of the requested candidate.
- `filters`: existing `StoneSearchFilters`.
- Versioned settings: `per_engine_limit=5`, `pool_limit=10`, `rrf_k=60`, equal engine weights.

Output: ordered candidates containing the card, internal stone ID, stable external ID, per-engine ranks and contributions, RRF score and final retrieval rank. Preserve the engine lists in trace output, including candidates removed by the pool limit.

Use this calculation in application code:

```text
score(stone) = sum(1 / (60 + rank_in_engine))
```

Ranks start at 1. An absent result contributes zero. Deduplicate within each engine by internal stone ID before assigning contiguous ranks; a stone receives at most one contribution per engine. Merge across engines by internal ID. Sort by score descending, then external ID ascending. Sort using full precision; round only for display.

Example: ranks 1 and 2 produce `1/61 + 1/62 = 0.032522...`; rank 1 in one engine only produces `1/61 = 0.016393...`. This is a ranking heuristic, not a probability of suitability. The constant 60 is an explicit initial experiment setting, not an assumed optimum or a dependency default.

Retain lexical and semantic entry points for independent searches and comparisons. Build typed hybrid hit/result DTOs in the search feature. Native engine scores may be recorded for diagnostics but are not added together. If payloads differ for a shared ID, use the Typesense card for this initial pool, record the mismatch, and load the authoritative PostgreSQL card after selection.

A hybrid operation uses two underlying search calls; account for both against the existing four-call retrieval allowance. It also embeds the semantic query. Avoid additional search-LLM iterations to decide whether to call the second engine. Empty successful lists are valid; a backend failure fails this operation visibly. Recovery and automatic retries are outside this change.

## 2. Explain every candidate in Langfuse

Use the existing request trace_id and compact custom observations:

```text
question
  search_stones_hybrid
    typesense_search
    qdrant_search
    rrf_fusion
  select_candidates
  read_candidate_cards
  verify
  evaluate_candidates
```

Record:
- Actual queries, exact filters, embedding model, limits and fusion version/settings.
- Ordered IDs returned by each engine, duration and result/error status.
- For each stone: internal/external IDs, name, lexical/semantic ranks (null if absent), both contributions, total score, fused rank, payload mismatch, and kept/dropped-by-pool-limit decision.
- Selection: input pool IDs, selected IDs, selection model and its output; record every unselected pool ID.
- Evaluation: connect the same ID to verified availability, source checks, conditional rules and final disposition.

Derive the retrieval explanation from recorded numbers: “Typesense #2 + Qdrant #1; RRF 0.032522; pool rank #1.” Do not ask an LLM to invent this explanation. A missing selection explanation is recorded as unselected, not an inferred rationale.

Store source text once using the existing trace reference mechanism. Search rank metadata is not a quoted source_ref and must not enter the evidence validator as one. Do not add noisy framework Runnable observations.

## 3. Prepare queries and exact filters

The parsing model returns RetrievalProposal: English lexical/semantic queries and an optional candidate_type with a fragment_id. It cannot supply a filters object. Code resolves the proposal into RetrievalRequest using the current corpus language en and AVAILABLE status; preparation stays in the existing parsing flow without another LLM call.

- “Find a granite for a quiet home”: candidate type filter GRANITE; quiet-home description goes into the queries.
- “Find a stone; a granite already lives here”: GRANITE is a household compatibility target, not a candidate type filter.
- Preserve exact names, IDs and case numbers; do not translate them.
- Active questions, fixture texts/names and prompts are English-only during stabilization. Prepare English lexical keywords and a semantic description; preserve the question and both prepared queries in the trace. Do not add requirements while preparing queries.
- Do not prefilter on model-inferred socialization traits, care levels, size, shelter, or IDs in the pilot parser. Keep those requests in assessment criteria/text queries. StoneSearchFilters remains available to explicit service/tool callers; the parser does not control those fields.
- Code applies indexed AVAILABLE and corpus language en for general recommendation retrieval; final PostgreSQL verification remains mandatory. Track stale-index omissions separately. Status-only questions keep their direct reference route.

Candidate-type and typed agreement proposals are verified in a separate ground_question stage using the configured evidence/evaluation model. It receives the original question, exact fragment-bound proposals, and the entire selected Typesense concept/example catalog. Only supported proposals become filters/facts. An unverified candidate type blocks the dependent recommendation instead of silently broadening it. Unsupported agreement values are not inverted and remain unknown to condition checking. Python verifies complete, unique proposal IDs and exact original quote/fragment binding; these structural checks do not themselves prove semantics.

The catalog is independently searchable/editable and contains no runtime regex rules. Definitions and contrasting English examples live in Typesense; seed/export files support initialization and repeatability. Selected language/version and the full snapshot hash are traced. Catalog unavailability and invalid model responses are explicit technical failures, separate from valid semantic unknown. Ten held-out questions and a frozen historical binary baseline support a separately authorized quality comparison, which has not yet been run.

Absent parser collections default to fresh empty lists, including requirements/preferences groups. Explicit null collections and malformed nonempty references remain validation errors; recommendation_limit remains required. This prevents an omitted empty compatibility list from blocking all retrieval without hiding invalid evidence or changing criteria.

Negations remain explicit in the parsed assessment criteria. Retrieval may legitimately find contradictory evidence, such as Madame Obsidian's vacuum trigger. High similarity must not be interpreted as confirmation.

## 4. Measure candidate loss before changing the shortlist

Selection input now includes the parsed SearchCriteria (requirements, preferences, household facts, requested availability/compatibility and count) and parsed ReferenceRequest. The original question remains source context only. Selection must not reinterpret these groups or treat an existing household type as a candidate-type requirement. Missing criteria stop selection with missing_criteria instead of triggering a second interpretation.

Initial workflow: hybrid pool of at most ten cards → existing LLM selection of at most three IDs → mandatory card/status reads → existing assessment and final ranking.

The pool limit, assessment shortlist limit and user-requested recommendation count are separate settings. Preserve the current shortlist cap in the first implementation so fusion can be evaluated independently.

For the current eleven-stone fixture set, prepare a separately authorized comparison that assesses all cards passing the same exact filters. Compare which relevant candidates disappear during retrieval, fusion and selection. Decide whether to expand or replace LLM selection only after this comparison. Never broaden paid assessment automatically.

## 5. Preserve exact routes and evaluate against baselines

Named status continues through the PostgreSQL reference path. Exact compatibility continues through pair_key lookup. Named candidate retrieval keeps exact-name/lexical behavior. Encyclopedia and event retrieval are outside this first fusion implementation.

Compare lexical-only, semantic-only and RRF over identical queries, filters, data and per-engine depth. Use equal final pool cutoffs and report the extra retrieval work of the hybrid mode.

Start with Q02/Q03 (quiet home), Q09 (vacuum contradiction), Q10 (children), Q16 (general sociability), and Q17/Q18 (two granites and source binding) from the [twenty-scenario manifest](../tests/fixtures/agent-eval/questions-challenge-20/README.md). Q18 also tests a known multi-name routing gap; do not attribute that failure to fusion.

Measure:
- Required-candidate recall at pool cutoff and after selection, using scenario-specific reviewed target sets.
- Rank of the first relevant candidate and recall of necessary conflicting evidence.
- Grounding, current-status eligibility and final decision correctness.
- Retrieval latency, embedding calls and model token/cost changes.

Do not treat all focus_stone_ids as expected recommendations: some are counterexamples. A larger pool alone is not proof of improved ranking. Archive actual inputs and per-stage results; never overwrite historical runs. Use deterministic checks for IDs, source labels, quotes, counts and RRF arithmetic; use semantic judging only for meaning.

## Implementation order and acceptance

Final local verification: 93 tests passed across unit, disposable-service integration and opt-in test collection; two paid tests skipped. Ruff and mypy passed; changed Python files pass formatting checks and git diff --check is clean. A complete graph test with fixture models and an in-memory Langfuse exporter verifies one trace_id, engine/fusion parentage, embedding identity, per-engine ranks, RRF arithmetic, selected/unselected IDs, PostgreSQL verification and the final candidate disposition. It also verifies that stale indexed AVAILABLE status cannot override a current RESERVED status.

Steps 4–5 complete: parsing now prepares a typed RetrievalRequest with English queries and exact filters. General recommendations execute exactly one hybrid operation; named recommendations use lexical lookup. The graph counts hybrid metadata retrieval_calls=2, rejects calls beyond the allowance, collects only retained pool cards and keeps full provenance separately. Selection consumes parsed intent and retrieval metadata. Engine and fusion operations have explicit named observations, with source documents referenced rather than repeatedly copied. Search-agent model calls and agent_model_id configuration have been removed; API/setup documentation and the current graph diagram reflect this change.

Step 6 local checks are complete. No paid call or cloud trace inspection was performed. The existing twenty scenarios remain planned model evaluations. Retrieval quality improvement, multilingual query quality, shortlist-loss measurement and model cost comparison are unproven until the explicitly authorized experiment; do not report them as passing based on fixture models.

Step 3 complete: StoneSearchService.search_hybrid strips and validates both queries, concurrently runs the existing lexical and semantic methods with shared filters/per_engine_limit, then applies RRF. TaskGroup cancels a pending sibling and propagates backend failures as ExceptionGroup; successful empty lists remain valid. The search_stones_hybrid tool returns JSON-serializable typed results with fixed initial settings and metadata retrieval_calls=2. Six offline orchestration/tool tests cover concurrency, filters, limits, embedding invocation, both failure directions, query validation and serialization. The registration integration scenario now exercises the tool against disposable Typesense/Qdrant services and checks ranks and RRF score. The tool is registered in the shared tool factory and is now invoked by the deterministic graph route. Two-call accounting and trace integration have since been completed as described below.

### Deferred experiment: cross-encoder reranking

After the hybrid baseline is measured, compare the same retrieved pool with RRF top-three, current LLM selection and a pretrained cross-encoder. A cross-encoder scores query/card pairs for relevance; it does not replace source validation, PostgreSQL availability or household condition rules. Check English questions/cards, required-candidate and contradictory-evidence recall at three, latency and cost. Preserve the same queries, filters, cards and evaluation targets across variants. Try an existing library/API rather than training a model or building a ranking library. No new dependency or reranker is part of the current pilot implementation. Multilingual comparisons are deferred beyond English stabilization.

Step 2 complete: HybridSearchSettings, HybridStoneHit and HybridSearchResult are defined in search_contracts.py; the pure fuse_stone_results function is in search/stones/rrf.py. Card IDs and external IDs are carried by each hit's typed card. Results retain deduplicated engine ID lists and both selected and dropped hits. The function consumes already bounded backend lists; per_engine_limit will be applied by step 3 orchestration. Nine offline tests cover arithmetic, overlap, disjoint/empty lists, duplicate handling, tie-breaking, payload mismatch, pool cutoff and full-precision ordering. The initial 44-test unit suite passed at step 2; see the final verification below.

Progress: step 1 uses current contracts only. Obsolete DTOs and compatibility branches have been removed; the active replay fixture and tests follow CandidateEvidence. Current source-reference validation uses structured Pydantic errors, including wrapped parser errors, rather than scanning model text. Missing candidate source labels are diagnosed separately from unsupported quotations. Verification: 69 unit/integration tests passed, one paid-model test skipped; Ruff, mypy and diff checks passed. Later steps are covered by the completion record below.

1. Remove obsolete assessment DTOs and compatibility paths; update active fixtures and tests to the current schema and fix types and formatting. Verify source_ref rejection and diagnostic behavior before attributing failures to retrieval.
2. Add typed hybrid results and a pure RRF function. Test overlapping/disjoint lists, a duplicate within one engine, empty results, and deterministic ties with known expected scores.
3. Add concurrent backend orchestration and the hybrid tool. Test shared filters, card-only retrieval, call accounting and failure visibility using disposable services or controlled test doubles.
4. Wire query preparation, recommendation routing, candidate collection and selection to the hybrid result. Ensure the collector accepts the new tool/output shape and preserves metadata instead of discarding it through setdefault.
5. Extend the existing trace handler and offline tests. Verify that each selected ID can be followed from both engine lists through fusion, PostgreSQL verification and final disposition.
6. Run local unit/integration checks, Ruff, mypy and diff checks. Review the change before explicitly authorized model comparisons.

Implementation locations: `search/stones/stone_search_service.py` and `search_contracts.py`; `assistant/tools.py`, `selection.py`, `workflow.py`, `tracing.py`; dependency wiring only where required. Reuse the existing application resource assembly.

Done means arithmetic and routing tests pass, provenance is inspectable in an observed trace, and the approved comparison is archived with stage-level results. Implementation can be complete before measurable quality improvement is demonstrated; report those outcomes separately.

## Search review: educational priorities

Sol 6.1 high and Astra medium independently reviewed the current search/agent code and exchanged critiques. Ingestion and production infrastructure were excluded. Both consider the deterministic RRF/provenance, PostgreSQL status recheck, original source/quote binding, separate individual/type scopes and Python condition checking strong foundations. Their agreed priorities follow; these are future work unless explicitly marked fixed.

1. **Complete event-based discovery.** PY-042 now connects named overview/history to the full PostgreSQL timeline and candidate assessment to observation events for shortlisted cards, preserving event UUID/date/type and parent card/case. Profile/preferences outrank observations, which outrank biography and encyclopedia; reference history has a separate scope. Current availability is still verified from PostgreSQL. The remaining path is event search → stone IDs → card/status: loading history after a card-only shortlist cannot discover a stone whose relevant fact exists only in an event. Preserve event subject and time; a neighbor's dislike of noise is not Svetlana's personal dislike.
2. **Close evidence/answer coverage gaps.** Candidate assessment omits stone_size, profile.care_level and health_notes despite their presence in the card. Exact-pair reference lookup saves the document in sources but not context_sources, leaving questions about the reason/conditions with a verdict only. Recommendation explanations accept a known candidate ID without checking every evidence ID belongs to that candidate; filtering unknown citations out later leaves the prose ungrounded. Add small regressions for each gap before broadening prompts. Structural citation checks still do not prove semantic truth.
3. **Keep intent coverage explicit.** PY-043 now executes mixed reference and recommendation goals with a bounded tool union, reference-first graph routing and deterministic result combination. Named information identity and recommendation target are separate; requested compatibility has explicit candidate/named_stone/types roles with shape and original fragment validation. Known/unsupported care and completed reference evidence survive partial candidate results. Fixture-model graph regressions cover both successful and partial mixed flows; live parsing/answer completeness remains unmeasured. Named recommendations still use general lexical lookup rather than the exact PostgreSQL name/ambiguity path used by references.
4. **Measure losses at the correct stage.** With per_engine_limit=5 and pool_limit=10, RRF pool cutoff currently cannot drop an item from the union. Measure engine recall@5, union recall, selection@3, assessed eligibility and final answer completeness separately. Svetlana survived retrieval/fusion but was omitted by selection. Compare RRF top-three, LLM shortlist and assessment of the same full small pool; do not conclude RRF is faulty from a shortlist failure. Check compound requirements individually rather than assuming one fragment proves every clause.
5. **Make the agent's next decision educationally useful.** The planner currently chooses an order for a tool set largely fixed by Python. Compare its value with a deterministic plan, or later give it one bounded source-selection decision: history versus type knowledge, which observation to search, whether evidence suffices. Avoid an unrestricted loop. Track input tokens, evidence counts and finish_reason per stage; Professor Quartzless's hundred events can test relevant-event retrieval versus complete chronology without dumping the whole timeline into every prompt.

The new grounding verifier checks supplied agreement/candidate-type proposals, not parser omissions, household presence or every requirement. Its held-out benchmark does not establish parsing → search quality. Add a compact end-to-end suite covering a positive control, counterexample, history, mixed intent, multiple entities and care. Future multilingual routing uses an English working representation while retaining original questions, entity IDs and evidence spans; it remains unimplemented and unmeasured.
