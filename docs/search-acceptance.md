# Search acceptance criteria and test coverage

These agreed criteria describe the current English search workflow. The coverage
review below is a static review of test targets and assertions, not a test run or
proof that every criterion passes. Existing search checks carry acceptance
markers; the six approved removals and duplicate cleanup are described below. Catalogue loading is happy-path preparation; catalogue CRUD and
production infrastructure completeness are outside this acceptance scope.

## Orchestration

| ID | When | Then |
| --- | --- | --- |
| AC-FLOW-01 | A question requests reference information, recommendations, or both. | The corresponding branches execute. A completed reference result survives a stopped recommendation branch in a mixed question. |
| AC-FLOW-02 | Generic candidate retrieval starts. | Lexical and semantic engines receive their intended queries and consistent filters. A backend failure remains distinguishable from a successful empty result. |
| AC-FLOW-03 | Retrieval returns candidates. | The shortlist contains only unique retrieved IDs, at most three. Selected cards are read, current statuses checked, evidence collected, and decisions calculated. An invented model ID cannot become a candidate. |

## Individual rules

| ID | When | Then |
| --- | --- | --- |
| AC-QUESTION-01 | A question contains requirements, preferences, a requested candidate type, and existing household stones. | These roles remain separate and bound to question fragments. A preference does not become mandatory; an existing household type does not become a candidate-type filter. |
| AC-GROUNDING-01 | Parsed values require catalogue confirmation, or a material recommendation constraint is omitted. | Unsupported values are not applied. An incomplete or invalid parse blocks recommendation without silent repair. |
| AC-IDENTITY-01 | A question names an individual stone. | Exact identity is resolved. Ambiguity or absence produces an explicit outcome; another retrieved stone is not substituted. |
| AC-RETRIEVAL-01 | Both search engines return the same stone. | Results are deduplicated and fused using RRF, with deterministic ties and retained engine ranks/provenance. A hit outside the retained pool cannot enter the shortlist. |
| AC-AVAILABILITY-01 | Recommendation eligibility is calculated. | Current PostgreSQL status is authoritative. Indexed status and historical events cannot replace verification; unknown or unavailable status prevents recommendation. |
| AC-EVIDENCE-01 | Extracted evidence is used to assess a criterion. | The exact quote occurs in an allowed source and belongs to the correct stone, criterion, and observation. Foreign or invalid evidence cannot confirm the requirement. |
| AC-EVIDENCE-02 | Sources conflict or describe different scopes, individual versus type. | Competing evidence is retained. Character assessment follows profile, observation, biography, then type priority. General type knowledge cannot establish a mandatory individual trait. |
| AC-COMPATIBILITY-01 | A recommendation depends on compatibility and household agreements. | The exact type-pair verdict is used. Every required condition must be confirmed for the relevant household/pair. Intention, refusal, missing confirmation, and an agreement for another pair do not satisfy it. Individual cohabitation contradictions are evaluated separately. |
| AC-DECISION-01 | Evidence is available for the final decision. | Unknown or contradicted mandatory criteria prevent recommendation. An unmet preference affects ranking without independently excluding the stone. Python policy determines eligibility, ordering, and the result limit. |
| AC-ANSWER-01 | The final answer is rendered for the current English-only request. | The answer is in English. Calculated statuses, decisions, and pair verdicts are preserved. Generated explanations use only the candidate's permitted evidence. Invalid generation uses the supported-data fallback; identities and evidence from different stones are not mixed. |

## Linking criteria and scenarios

An AC identifies application behavior; a scenario identifies an input. A test may
cover several related AC, and a scenario such as Q04 may exercise several AC.
Existing checks use one marker per associated criterion:

```python
@pytest.mark.acceptance("AC-COMPATIBILITY-01")
@pytest.mark.parametrize("scenario_id", ["Q03", "Q04", "Q05", "Q06", "Q07", "Q08"])
```

Select associated checks without enabling paid evaluation:

```sh
uv run pytest tests/unit --acceptance AC-EVIDENCE-01
uv run pytest tests/unit --acceptance AC-QUESTION-01 --acceptance AC-GROUNDING-01
uv run pytest --collect-only -q --acceptance AC-COMPATIBILITY-01
uv run pytest --collect-only -q -m acceptance
```

Repeated `--acceptance` selects the union. An ID with no matching checks in the
collected paths is an error. Markers associate checks with the asserted part of an
AC, not proof of full coverage. Ordinary pytest execution does not enable paid
runners; their existing explicit opt-in gates remain unchanged. Measurement-only
runners, synthetic evaluator checks, and unrelated infrastructure checks are not
labelled as application acceptance gates.

Q02 exercises recommendation, evidence, availability, and decisions. Q03–Q08 vary
agreement conditions. Q13–Q15 and Q19 exercise current status versus historical
information. These are scenario associations, not claims of complete AC coverage
by the current runner assertions.

## Coverage review

Paths below are relative to the repository root. “Partial” names a specific
assertion gap. A stubbed graph checks application orchestration but does not
measure model understanding. Shared AC between graph and rule tests is not, by
itself, duplication.

### Assistant application tests

All paths in this table start with `tests/unit/assistant/`.

| File | AC association and actual assertion scope | Recommendation |
| --- | --- | --- |
| `test_hybrid_workflow_with_stubs.py` | FLOW-01/02/03, GROUNDING-01, RETRIEVAL-01, AVAILABILITY-01, ANSWER-01; real graph with fixed model replies, current status AVAILABLE/RESERVED/missing, fusion and trace propagation. DECISION-01 only for the provided candidate/status cases. | Keep orchestration. The duplicate RRF formula assertion was removed; provenance and handoff assertions remain. Detailed tracing still overlaps narrower tests. Preserve stage handoff and final outcomes. |
| `test_reference_workflow_with_stubs.py` | FLOW-01, IDENTITY-01, COMPATIBILITY-01, ANSWER-01; reference routes, missing data, exact pairs, fallback, and an eight-pair evaluation/answer subgraph. | Keep meaningful route variants. Later extract detailed rendering/fallback rules from graph scenarios rather than deleting their only coverage. The eight-pair case protects against silently truncating household pairs. |
| `test_retrieval_steps.py` | FLOW-02/03, RETRIEVAL-01; named lexical versus generic hybrid route, call budget, exclusion of dropped hits. | Keep. Budget and dropped-pool boundaries are absent from the graph happy path. |
| `test_reference_routing.py` | FLOW-01, QUESTION-01; independent reference/recommendation targets, mixed branch routing, preservation before continuation. | Keep direct routing checks; later remove repeated parse/setup assertions already covered by role/planning tests. |
| `test_reference_planning.py` | FLOW-01, QUESTION-01, IDENTITY-01; dependency order, status-only route, candidate versus named/type compatibility targets. | Keep negative dependency/target checks; a successful graph does not prove rejection of a bad plan. |
| `test_reference_results.py` | FLOW-01, ANSWER-01; mixed source-ID collision and evidence preservation at a budget stop. | Keep. These are distinct counterexamples, not duplicates of successful mixed routing. |
| `test_reference_lookup.py` | IDENTITY-01; different reference and recommendation names resolve independently. | Keep; current graph examples do not replace the distinct-two-name assertion. |
| `test_named_candidate_selection.py` | IDENTITY-01, FLOW-03; resolved ID missing from retrieval, model proposing another ID, ambiguous/missing name. | Keep. Named selection is different from generic shortlist membership. |
| `test_candidate_selection.py` | QUESTION-01, FLOW-03; parsed intent reaches selection; shortlist normalization preserves model order, removes foreign/duplicate IDs, caps at three, and rejects truncated/missing/invalid output. | Keep. FLOW-03 shortlist boundaries are covered; parser quality remains a separate gap. |
| `test_candidate_ranking.py` | DECISION-01; direct score aggregation and deterministic order, total and compatibility priorities, external-ID tie-break, limit and dispositions. | Keep. It tests supplied reasons; it does not prove how `evaluate_candidate` maps an unmet preference into its ranking score. |
| `test_candidate_admission.py` | DECISION-01; confirmed/unknown/contradicted finding as requirement versus preference through `evaluate_candidate`. | Keep. Admission is covered; preference-only score impact remains unasserted. |
| `test_semantic_role_contract.py` | QUESTION-01, GROUNDING-01; one parser/auditor catalogue revision, failed load, optional/negated candidate type, household versus mandatory compatibility, no parse repair. | Keep behavior checks. The duplicate hard-compatibility test was removed from `test_compatibility_conditions.py`; the richer role comparison remains here. |
| `test_question_grounding.py` | QUESTION-01, GROUNDING-01, FLOW-01; source-bound decisions, coverage rejection, zero-proposal audit, independent atoms, operational-filter rejection. | Keep rule/negative cases. Exact schema-description wording assertions were removed. The authored holdout-data check remains separate from acceptance associations. Some tests combine node and routing checks and can later be split without losing assertions. |
| `test_parser_empty_lists.py` | QUESTION-01 and current input validation; missing optional groups retain required criteria, malformed input is rejected. | Keep the meaningful missing-list case. The mutable-default check was removed; malformed current-input validation remains. |
| `test_compatibility_conditions.py` | QUESTION-01, COMPATIBILITY-01; all conditions, partial confirmation, refusals/conflicts/foreign scope, unmarked pair, invalid authored rule. | Keep condition rules. The duplicate hard-role assertion and obsolete-field rejection were removed. The parse-and-conditions test itself currently combines two rule targets. |
| `test_source_references.py` | EVIDENCE-01/02; source versus quote validity, error classification, separate criterion atoms, profile/observation/biography priority, authoritative event IDs, and type-only evidence not proving an individual requirement. | Keep. EVIDENCE-01 still lacks a few foreign-candidate/criterion/event counterexamples; EVIDENCE-02 does not directly compare biography with type evidence for a conflicting preference. |
| `test_compatibility_policy.py` | COMPATIBILITY-01, EVIDENCE-02, DECISION-01; individual cohabitation contradiction versus pair verdict, preference versus veto, missing agreement, and lookup-only facts. | Keep. The final conditional disposition for positive individual evidence with a missing agreement is not asserted in this focused policy check. |
| `test_assessment_context.py` | EVIDENCE-02, partially EVIDENCE-01; character context keeps conflicting original evidence and excludes unrelated chapter sections. | Keep. Context preparation and evidence precedence test different functions. The unstructured-source case is a current input behavior, despite its incidental source ID containing `legacy`. |
| `test_candidate_observations.py` | EVIDENCE-01/02, ANSWER-01, partial DECISION-01; only OBSERVATION events enter assessment with authoritative IDs, conflicting character evidence excludes the candidate, evidence reaches answer sources. | Keep observation-loading assertions. Answer-source rendering overlaps `test_candidate_answer.py`; consolidate only after preserving a handoff check. Calls assessment and answer nodes directly, not a full graph. |
| `test_reference_evidence.py` | EVIDENCE-01/02, ANSWER-01; non-verbatim/unknown quotes and cross-scope citations are rejected. | Keep. Reference and candidate evidence use different validators. |
| `test_candidate_answer.py` | ANSWER-01; per-candidate allowed IDs, foreign/unknown/missing citations, shared encyclopedia/pair evidence, supported fallback. | Keep the parameterized rule checks. They do not prove free-text semantic correctness. |
| `test_strict_structured_output.py` | Supports EVIDENCE-01 and current provider contract: strict wire schema, parsed DTO validation, malformed JSON, bounded provider metadata. | Keep provider-adapter checks separately from acceptance rules. Exact HTTP schema behavior is not redundant with direct DTO tests. |
| `test_workflow_tracing.py` | No direct search AC; application callbacks expose model/decision data and suppress framework noise. | Keep outside the AC suite: trace inspection is part of the learning workflow. Do not count a small artificial graph as search-behavior coverage. |
| `test_provider_error_tracing.py` | No direct search AC; application callback links provider failure metadata to generation and stage. | Keep separately; failure tracing differs from successful tracing. |

### Search rules and adapters

| File | AC association and actual assertion scope | Recommendation |
| --- | --- | --- |
| `tests/unit/search/test_hybrid_search.py` | FLOW-02; concurrent engines, matching filters/limits, empty queries, failure propagation/cancellation, tool result and two-call metadata. | Keep. A backend failure is not an empty result; metadata declaration is distinct from workflow budget consumption. |
| `tests/unit/search/test_rrf.py` | RETRIEVAL-01; overlap, disjoint lists, duplicates, empty engines, custom k, cutoff, payload conflicts, precise tie ordering. | Keep compact parameterized rule coverage. Remove repeated arithmetic assertions from graph tests later, not these counterexamples. |
| `tests/unit/search/test_encyclopedia.py` | Indirect EVIDENCE-01/02 support; actual document builder preserves source path, type scope, and source sections. Also checks the exact fixture inventory. | Retain transformation/source-scope checks. Fixed chapter names/counts can be reduced; catalogue inventory is outside the acceptance scope. |
| `tests/unit/search/test_stone_compatibility.py` | Indirect COMPATIBILITY-01 support; builder creates stable unique source IDs and pair/type documents. Also checks exhaustive fixture counts. | Retain source identity and pair transformation. Exhaustive 55/10/1/66 inventory assertions are candidates for reduction, not the whole builder test. |
| `tests/integration/search/test_typesense.py` (removed) | No independent search AC; authenticated debug/version smoke check. | Removed; real indexing/search integration checks exercise the client. |
| `tests/integration/search/test_grounding_catalog.py` (removed) | Catalogue reload/search/edit inventory; outside these AC. Called search/edit routes absent from the current router. | Removed as an obsolete API contract. |
| `tests/integration/search/test_knowledge_indexing.py` | Reference search tools support FLOW-01/COMPATIBILITY-01. Another test verifies reload source isolation and exact indexed counts. | Keep tool lookup happy path. Treat reload/inventory coverage separately; source-isolation behavior is application code, not a synthetic judge check. |
| `tests/integration/stones/test_register_stone.py` | Mixed file: search-tool/current-status, detail, and event tests support FLOW-02/03, IDENTITY-01, AVAILABILITY-01, EVIDENCE-01. Registration persistence/validation/rollback are outside search AC. | Keep real search/read-tool integration coverage. Registration tests need a separate scope decision; no blanket deletion because the filename says registration. Fixed-vector semantic search checks backend plumbing, not embedding relevance. |

### Application evaluation runners

| File under `tests/evaluation/` | AC association and limits | Recommendation |
| --- | --- | --- |
| `test_full_run_evaluation.py` | Real workflow/model run; archives actual output and applies shared failure checks for reviewed retrieval coverage, structured expectations, counterexamples and dispositions. Captures parser/auditor state separately. | Keep. Parse targets are not reviewed for the challenge scenarios, and final prose remains ungraded. |
| `test_candidate_assessment.py` | EVIDENCE-01/02, partial DECISION-01 on a frozen quiet-home input. Asserts DTO/grounding/coverage/no invented compatibility checks. Candidate policy outputs are recorded, but not all decisions/ranks are independently asserted. | Keep isolated extraction evaluation; not a duplicate of full runs. |
| `test_grounding_model_evaluation.py` | GROUNDING-01 measurement on reviewed holdout parses. Requires exact case execution and usable outcomes; optional acceptance mode compares every outcome to its reviewed case label. It does not invoke the question parser. | Keep. Acceptance is opt-in and per-case; this narrow holdout does not establish parser quality or general model reliability. |
| `test_saved_run_evaluation.py` | Offline structured/stage checks for the selected saved result, using the same failure policy as full-run execution. Positive retrieval targets gate engine union and retained RRF only, not later shortlist/answer stages. | Keep. It does not rerun the application or grade free prose. |
| `test_saved_run_geval.py` | Diagnostic EVIDENCE-01/02 grading of one saved quiet-home extraction. Judge completion is asserted; the uncalibrated score threshold is diagnostic. | Keep separately from deterministic gates; it does not establish general final-answer quality. |

### Outside the search acceptance scope

- `tests/unit/core/test_lifespan.py`: application resource initialization/disposal;
  retain as infrastructure regression.
- `tests/unit/core/test_unit_of_work.py` and
  `tests/integration/core/test_unit_of_work.py`: some commit/rollback cases overlap
  at two levels. Real persistence tests establish commit/rollback outcomes; unit
  error-cleanup and context-guard cases protect different behavior. Candidates for
  consolidation are the three simple unit success/rollback scenarios, not the
  unique failure/cleanup cases.
- `tests/unit/core/test_settings.py`: environment mapping is a useful application
  configuration check. The constructor field-copy check was removed. Built-in required-field and
  bounded-port checks remain outside search AC.
- `tests/integration/core/test_application.py`: one application/OpenAPI smoke
  check; no search AC. Retain unless the general smoke suite is explicitly removed.
- `tests/integration/core/test_database_engine.py`: basic connection/session
  factory checks overlap database-backed integration tests. Potential general
  infrastructure cleanup, not a missing search-AC problem.
- `tests/synthetic_evaluation/test_reference_answer_assertions.py` calibrates a
  judge on prepared answers. The nine `test_*.py` files under
  `tests/synthetic_evaluation/unit/` check evaluator logic, fixture expectations,
  metrics, source rehydration, and run records. They do not establish application
  search AC. Their own criteria and cleanup review remain separate.

## Implemented cleanup

Six approved test functions were removed:

| Test | Location | Reason |
| --- | --- | --- |
| `test_current_model_dto_rejects_accommodation_verdicts` | `tests/unit/assistant/test_compatibility_conditions.py` | Protects a retired field rather than current search behavior. |
| `test_optional_groups_and_lists_do_not_share_mutable_defaults` | `tests/unit/assistant/test_parser_empty_lists.py` | Primarily checks Pydantic collection defaults. |
| `test_explicit_hard_compatibility_requirement_remains_mandatory` | `tests/unit/assistant/test_compatibility_conditions.py` | Included in the richer household-context versus mandatory-role check. |
| `test_typesense_client_authenticates_against_container` | `tests/integration/search/test_typesense.py` (file removed) | Real search integration tests exercise the same authenticated client. |
| `test_catalog_reload_search_edit_and_complete_version_read` | `tests/integration/search/test_grounding_catalog.py` (file removed) | References removed catalogue CRUD routes. |
| `test_database_settings_accept_valid` | `tests/unit/core/test_settings.py` | Copies constructor input to fields without checking search policy. |

The hybrid graph no longer repeats the exact RRF formula asserted by dedicated
RRF tests. The grounding audit test no longer asserts exact prose in schema
field descriptions; it still checks the current schema and application behavior.
No new acceptance scenarios or gap tests were added.

Other proposed consolidations remain unimplemented because they protect distinct
behavior: reference fallbacks, observation-to-answer provenance, document builder
source identity, malformed current input, and transaction failure cleanup.
Catalogue inventory and holdout fixture checks were not deleted merely because
they sit outside the search AC. Synthetic criteria remain a separate discussion.

## Current partial coverage

The following parts remain unestablished by current assertions; none should be
reported as fully covered just because a test carries its AC marker:

- **QUESTION-01 and GROUNDING-01:** the real parser is not measured against
  reviewed role/fragment targets in the challenge scenarios. The grounding holdout
  uses prepared parses and does not establish parser quality.
- **IDENTITY-01:** ambiguity and not-found outcomes are tested from prepared
  resolver states; real ambiguous-name database resolution is not independently
  evaluated.
- **EVIDENCE-01:** no focused negative application-validator cases were found for
  a finding with another candidate's `stone_id`, a mismatched criterion/fragment,
  or a valid observation belonging to another candidate.
- **EVIDENCE-02:** the profile/observation/biography priority and type-only
  mandatory restriction are covered. Biography versus type evidence under a
  conflicting preference lacks a direct comparison assertion.
- **COMPATIBILITY-01:** pair and individual policy conflicts are covered, but the
  focused policy test does not assert the final conditional disposition for
  positive individual evidence with an unconfirmed household agreement.
- **DECISION-01:** admission, score aggregation, ordering and limits are covered.
  The score impact of an unmet preference produced by `evaluate_candidate` is not
  directly asserted.
- **ANSWER-01:** the evaluation report carries the actual answer, actual supplied
  sources and structured decisions as judge input. Semantic application grading
  remains unmeasured; prepared-answer judge calibration is not an application
  answer result. A manual review of the archived Q04 run found its generated
  explanation was Spanish despite an English question, so the current English
  response requirement is not reliably established by the saved run. This is a
  single-run finding, not a general model-quality measurement.

The full-run and saved-run evaluators now fail on missing required reviewed
measurements. Retrieval coverage probes gate the engine union and retained RRF
pool only; they are not exact shortlist or answer oracles. Grounding acceptance
can compare each holdout result with its existing reviewed label, but this does
not grade the parser or free-form application answers. No numerical aggregate
quality threshold is asserted.

## Current boundaries

Observations are read after shortlisting, so observation-only facts cannot be
assumed to discover a stone. Assessment sees a supported subset of card fields.
Pure reference questions without sensitive proposals do not undergo the same
recommendation coverage audit. Valid quotes and source IDs do not prove semantic
entailment of generated prose. Synthetic evaluator acceptance is a separate topic.
