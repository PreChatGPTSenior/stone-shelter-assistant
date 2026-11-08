# Retrieval and assistant learning requirements

Updated: 2026-11-08 (JSON compatibility source and separate tarot deferral). Learning direction: [ADR-0006](../adr/0006-rag-and-agent-learning-focus.md). Selected retrieval architecture and experiment plan: [ADR-0016](../adr/0016-typesense-lexical-qdrant-vector-experiments.md).

This document captures the discussion's accepted direction, desired behavior, proposed exercises, and open choices. It is a learning backlog, not an assertion that the capabilities exist or a scheduled implementation plan. GitHub Issues and the project board track delivery. The [pilot delivery plan](../search/pilot-delivery-plan.md) separates the immediate path from later experiments.

**Domain premise:** this is a fictional world where stones are pets. Personality, socialization, health, past experiences and family wishes are intentional domain facts authored by staff. Scientific realism is not the goal. Keep fictional sources distinct from the geological encyclopedia, without treating fictional data as invalid merely because real rocks do not have these attributes. See [ADR-0009](../adr/0009-fictional-pet-stone-profiles.md).

## Active delivery priority: HAPPY PATH PILOT FIRST

The [project manifesto](../project-manifesto.md), accepted on 2026-10-31, governs current sequencing. Build the first connected search/RAG result with prepared source documents, Typesense, Qdrant, LangChain, LangGraph, and minimum useful Langfuse tracing. Keep code quality high and scope narrow. Evaluation frameworks, comprehensive datasets, resilience, synchronization workers, elaborate versioning, and broad comparison studies below are subsequent learning work, not prerequisites for the pilot. Earlier sequencing suggestions and broad ticket criteria must not block that first working path.

## Source-first planning update (2026-11-08; amended by ADR-0018)

[ADR-0017](../adr/0017-source-first-tool-routed-pilot.md) and the [OpenSpec task map](../search/pilot-delivery-plan.md) define the current order: operational examples and the encyclopedia, then the complete authored JSON type-compatibility source, then shared preparation/indexing/retrieval. ADR-0018 supersedes immediate astral authoring: tarot is a separate deferred idea. Current pilot source preparation is first; no exhaustive relevance dataset is required before the pilot. PY-027/PY-028/PY-029/PY-030 are local proposed task IDs until explicitly published to GitHub.

The first connected result includes actual LLM tool selection inside a bounded LangGraph, typed exact SQL/hybrid/reference/details operations, grounded answers and minimum useful Langfuse tracing. A fixed answer chain alone does not complete the pilot. One model/provider is enough initially; full evaluations, second-provider studies, complete budgets and richer graph behavior remain later work. JSONL is not an application intermediate; optional corpus/result snapshots belong to later experiment tooling.

## Status vocabulary

- **Implemented:** present in the repository with the evidence stated below.
- **Accepted direction:** chosen scope or boundary; implementation may not exist.
- **Planned capability:** desired behavior discussed for a later increment.
- **Proposed exercise:** a recommendation to explore, not an irrevocable architecture decision.
- **Deferred:** explicitly not required now.
- **Open:** needs a concrete decision before implementation.

## Current decision precedence

The current entity and ingestion contract is [docs/domain/model.md](../domain/model.md), with ADR-0013 and ADR-0015: one stone with a required case, source-provided adoptionStatus, optional profile, and 1 to 100 events containing ADMITTED. RETURNED replaces the historical UNDER_REVIEW vocabulary. Earlier ingestion and profile discussions in this learning backlog are context; they do not override that model or imply unimplemented updates and lifecycle actions.

Typesense for lexical retrieval and Qdrant for vector retrieval are selected under ADR-0016. Local Typesense infrastructure, validated settings, an async SDK client, and lifecycle wiring are implemented; indexing and retrieval are pending. Qdrant runs as a local Compose service, while its Python client, vector collections, indexing and retrieval remain pending. pgvector and Solr are deferred comparison options. The experiment plan is accepted; exact search APIs, schemas and later client choices remain future work.

## 1. Existing baseline

| Item | Status and evidence |
| --- | --- |
| uv, FastAPI, Pydantic, SQLAlchemy async, asyncpg, Alembic, PostgreSQL | Implemented foundation |
| Validated connection settings, application lifespan, explicit UoW | Implemented in PY-002 |
| Stone and related records | Implemented through PY-010: internal/external UUIDs, stone properties, optional profile, required lifetime case, current shelter/status, and life events. Admission belongs to the case, not Stone. |
| Type and size | Python enums at input/domain boundaries; database columns are VARCHAR(32), without enum CHECK constraints |
| Stone creation | Implemented: POST `/api/v1/stones`, explicit commit, HTTP 201 with exactly `{"id": "<UUID>"}` |
| Field ownership | Internal UUIDs, relationship FKs, technical dates, and ORM versions are hub-managed. External IDs, current shelter, adoption status, admission date, and event facts come from the source. |
| Validation | Pydantic trims string fields; nonblank name up to 120 Unicode code points and biography up to 2048; enum values checked |
| Contracts | Validated nested registration DTOs map directly to ORM entities through the service; no intermediate domain dataclass conversion is required. See the domain model for aliases and field ownership. |
| Database schema | Five business tables in stone_shelter; Alembic version tracking in public. Local application data persists; tests use disposable Testcontainers. |
| Scenario tests | PY-010 verification: make check passed with 41 tests, covering HTTP registration, rejected input, loader behavior, and atomic graph rollback. |
| Development checks | make check runs Ruff autofix/formatting, mypy, and pytest. Testcontainers migration setup runs Alembic upgrade/check; no test cleanup targets local application data. |
| Encyclopedia corpus | Imported English Markdown with ten rock types, comparison table, care guidance, and source/editorial notes; see [provenance](../../stone-rules/stone-encyclopedias/README.md) |
| Delete and Read | Not implemented at this decision point; the earlier Delete plan is superseded by retained records and state updates in ADR-0008 |
| Typesense connection | Compose service, TypesenseSettings, official async SDK factory, lifespan ownership, and disposable Testcontainers fixtures are implemented. Collections/indexing/retrieval remain pending. |
| RAG and agent runtime | LangChain text splitting is installed for encyclopedia preparation. LangGraph, embeddings, Qdrant, and answer generation remain unimplemented. |
| Model providers | Ollama and OpenRouter selected for future experiments; no provider integration is implemented by these decisions |
| LLM observability | Langfuse Cloud Hobby selected; account setup, credentials, SDKs, and tracing exports are not configured |

The corpus distinguishes geological characteristics, practical interpretations, approximate ratings, and fictional personalities/rituals. Preserve those distinctions during ingestion and answering.

## 2. Product and learning boundaries

**Accepted direction:** the owner understands the basic Python backend construction and now prioritizes unfamiliar retrieval and AI engineering over completing a familiar CRUD product.

- The catalog is a source of real specimen records. A plain list/read surface can support inspection without a filter-heavy UI.
- Users express filtering, search, comparison, and selection needs through the assistant.
- The upstream emulator submits one complete stone/case JSON per HTTP request. It can iterate multiple files, but the API does not accept a multi-stone batch. Manual product entry is not the intended user workflow.
- Existing creation logic may support ingestion. Indexing and embedding consistency are the next reasons to revisit the write path.
- Add catalog reads needed for tools and useful inspection. Physical deletion is not planned. Registration and basic population are implemented; partial updates and later event append remain separate future capabilities.
- A complete UI, user-created stone form, photo upload/MinIO integration, authentication, and Redis integration are deferred. ShelterCase snapshots and event persistence are implemented; application-owned lifecycle commands remain deferred.
- Existing Java/product/UI documents provide context. They do not automatically expand the new scope.
- The later comparison target is the same RAG behavior implemented with Spring AI.

Update: section 3.1 and [ADR-0007](../adr/0007-lifetime-shelter-case-identity.md) refine the user audience and ingestion model. Adoption lifecycle snapshots and event persistence are implemented; chatbot-driven state changes and a full UI remain outside the initial assistant scope.

## 3. Information sources and future ingestion

**Accepted direction:** combine operational pet data with distinct reference sources. The Markdown encyclopedia and JSON type-compatibility guide are separate reference sources, not fields to duplicate on every stone.

| Source | Responsibility | Status |
| --- | --- | --- |
| Operational database | Individual stones, profiles, current case state, shelter information, and life events | Registration implemented through PY-010; later event append/update APIs remain planned. See the [domain model](../domain/model.md). |
| Stone encyclopedia | General knowledge about rock types, conditions, care, and caveats; preserve the corpus distinction between geology and fictional material | English Markdown corpus already imported; retrieval not implemented |
| Type-compatibility guide | Authored fictional cohabitation guidance for all current types | English JSON authored in PY-028: ten portraits and all 55 unordered pairs. Parsing/indexing/retrieval remain pending. |
| Separate tarot idea | Potential future tarot-card divination program, not a current knowledge source | Deferred; former PY-029 astral-catalog plan is superseded by ADR-0018. |

Individual profiles and events are legitimate facts about pets in this fictional world. They are not merely decorative personality text, and general type-level guidance does not by itself establish an individual's suitability.

Requirements for combining these sources:

- Preserve source identity, version, and document/section or event identifiers so explanations can distinguish a general encyclopedia statement, a fictional compatibility rule, and a staff observation.
- Use current database state for availability and shelter responsibility. A compatibility document or historical event must not override authoritative current availability.
- Combine general knowledge with individual profiles and relevant life events. A generally compatible type pair does not guarantee that two particular pets are a suitable match.
- Do not silently merge fictional compatibility systems into geological claims or invent rules missing from the authored references.
- Reference routing currently distinguishes encyclopedia and compatibility. No astral/tarot source or tool is required.

**Planned capabilities:**

- Read the committed Markdown corpus rather than asking users to supply encyclopedic text when importing stones.
- Split knowledge into identifiable documents/fragments with source and version metadata.
- Preserve rock type and section identity; retain contextual caveats when extracting a section or comparison-table entry.
- Support repeat ingestion and reindexing without accidental duplicates or stale results.
- Physical deletion is no longer planned. When case state or other relevant data changes, update indexed information as needed and prevent stale availability from overriding current database state. Withdrawal/archive semantics are not yet defined.
- For asynchronous indexing, persist the business write and durable indexing intent in one PostgreSQL transaction; compute embeddings outside that transaction. This follows ADR-0004 and is not implemented yet.

### 3.1 Staff hub and lifetime case identity

**Implemented registration model through PY-010:** see [the authoritative domain model](../domain/model.md). ADR-0007 records the original identity decision; its earlier status vocabulary is superseded by the domain model and ADR-0015.

- The assistant serves employees at a hub for two shelters. Visitors describe preferences to an employee; no public UI is required for the pilot.
- Stone stores specimen identity and properties. StoneProfile is optional. Every registered stone has one required lifetime ShelterCase, which stores current shelter, source-provided adoption status, admission date, and associated CaseEvents.
- Internal UUIDs support database relationships. The source supplies distinct external UUIDs for stone, case, and events. The case number is a unique opaque string, not an instruction for calculating current shelter.
- Returns and transfers preserve stone identity, case identity, and case number. Shelter records contain name and address; two reference records are seeded separately.
- Source snapshots and historical events have different ownership. Registration stores both without replaying events to calculate current status or location.
- Final recommendations must check current availability and shelter against PostgreSQL before presenting an actionable candidate. The assistant and its retrieval adapters are not implemented yet.

### 3.2 Current adoption states and event history

The accepted current states are AVAILABLE, RESERVED, ADOPTED, and RETURNED. UNDER_REVIEW is historical vocabulary and is not a current enum value.

| Current state | Meaning for selection |
| --- | --- |
| AVAILABLE | May be recommended for a new adoption |
| RESERVED | Excluded from new available-candidate recommendations |
| ADOPTED | Excluded from available-candidate recommendations; retain records |
| RETURNED | Returned and not yet ready for adoption; excluded until readiness is separately confirmed |

The domain diagram describes AVAILABLE -> RESERVED -> ADOPTED, direct AVAILABLE -> ADOPTED, reservation end -> AVAILABLE, ADOPTED -> RETURNED, and RETURNED -> AVAILABLE after readiness confirmation. These describe the fictional lifecycle, not an implemented state machine or registration-time replay algorithm.

- Required shelterCase.adoptionStatus is supplied by the source and has no AVAILABLE default.
- Imported history contains ADMITTED in any position; ADMITTED does not reset the current state. Dates and array order do not calculate it.
- Transfer event types encode P1-to-P2 or P2-to-P1 direction. Current shelter comes from the source snapshot, not from replay or the case-number suffix.
- Authored scenarios with non-AVAILABLE current states contain a coherent history explaining them. The happy-path importer trusts upstream business consistency rather than enforcing a transition engine.
- Observations, care events, and adopter meetings remain evidence and do not automatically update a profile or current state.
- Future state-changing or append-event operations need explicit contracts; they are not prerequisites for the pilot.

### 3.3 Implemented ingestion and deferred mutations

[ADR-0013](../adr/0013-single-stone-ingestion.md), [ADR-0014](../adr/0014-persistent-local-application-database.md), and [ADR-0015](../adr/0015-source-owned-adoption-status.md) supersede the earlier batch and event-replay proposals.

| Concern | Current behavior |
| --- | --- |
| Registration | POST /api/v1/stones accepts one stone, required shelterCase, optional profile; no multi-stone wrapper |
| History on creation | 1 to 100 events including ADMITTED anywhere |
| Current state | Required adoptionStatus and currentShelterId supplied by the source |
| Persistence | DTO -> ORM graph; one session and one explicit UoW commit for stone, case, optional profile, and events |
| Response | HTTP 201 with exactly the internal stone UUID as id |
| Validation | Existing HTTP 422 envelope; CASE_EVENT_LIMIT_EXCEEDED and CASE_ADMITTED_EVENT_REQUIRED carry custom validation codes/context |
| Input files | fixtures/stones/<stone.externalId>.json; ten valid English request files; invalid examples are test-only |
| Loader | Sends one file per HTTP request; no automatic retries, replay no-ops, or duplicate skipping |
| Shelters | Separate fixtures/shelters.json reference seeding; existing records are preserved |
| Database targets | Persistent Compose PostgreSQL for the application; disposable Testcontainers for all database-backed automated tests |
| Deletion | No physical Delete endpoint in the accepted direction |

The initial local load of ten stones was verified during PY-010. This documentation synchronization does not reload data or rerun tests.

Partial updates, profile arrival after registration, and POST /api/v1/shelter-cases/{external_case_id}/events remain future contract work. Their DTOs, omitted/null semantics, responses, source ordering, duplicate/correction handling, and any state mutation rules are not implemented. Durable indexing intent under ADR-0004 and automatic synchronization are also later work. None blocks reading the prepared data for the pilot.

## 4. Fictional pet profiles and compatibility

**Implemented registration fields through PY-010:** [ADR-0009](../adr/0009-fictional-pet-stone-profiles.md) records their origin; [the domain model](../domain/model.md) defines the current exact vocabulary and constraints. Staff-authored profile properties belong to the individual Stone and persist across shelter transfers, returns and adoption cycles. ShelterCase continues to own adoption/accounting state and history.

| Profile concept | Representation | Meaning |
| --- | --- | --- |
| Socialization traits | Set of enum values assigned by staff | Multiple simultaneous characteristics, such as preferring no other stones while enjoying children |
| Care level | Enum/category | The required amount of care/attention |
| Health description | Free text | Fictional health observations, chronic conditions and relevant care details |
| Trigger/experience notes | Free text | Trauma, fears, prior experiences, sensitivities and triggers |
| Preferred environment | Free text | The pet-stone's wishes about its future family, home and surroundings |

Current behavior and future boundaries:

- Socialization shall allow multiple values without duplicate set members. It is not a single exclusive enum or numerical degree. Staff assign the values; the model must not silently overwrite them with inferred traits.
- Accepted values are PREFERS_SOLITUDE, ENJOYS_HUMAN_COMPANY, ENJOYS_OTHER_STONES, GOOD_WITH_CHILDREN, CAUTIOUS_WITH_STRANGERS, and NEEDS_SLOW_INTRODUCTION. Omission defaults to an empty set; null is not a valid set.
- Keep care intensity separate from the presence of chronic fictional conditions. Accepted care categories are STANDARD, ADDITIONAL, and INTENSIVE; null means unassessed and does not default to STANDARD.
- Record chronic conditions in the health description rather than creating an unrequested medical taxonomy or treating every chronic condition as intensive care.
- Triggers/experiences and preferred environment are text fields initially, not a mandatory catalog of structured trigger entities. Structured extraction can be explored later without losing the staff-authored source text.
- Preserve fictional observations as legitimate domain data. For example, fear of running water after an aquarium experience does not require proof of a geological sensitivity.
- An absent profile value means unknown. Do not infer no trauma, no care needs, child suitability or universal compatibility from missing data. Registration nullability, limits, and defaults are defined in the domain model. Partial-update clearing semantics remain future contract work.
- Existing geological and physical data may coexist with these traits, but they do not replace or invalidate the fictional pet profile.

### 4.1 Fictional compatibility JSON

The owner delegated complete creative authoring under [ADR-0018](../adr/0018-json-compatibility-and-deferred-tarot.md). The source is [stone-type-compatibility_en.json](../../stone-rules/type-compatibility/stone-type-compatibility_en.json), a provider-style English catalog with fictional attribution.

- All ten current StoneType values have a portrait; all 55 unordered pairings are present, including two distinct pets of the same type. Reversing type order selects the same record.
- Each entry has a stable ID, both types, verdict, title, explanation, household agreement, avoid guidance and bureau note. The catalog declares category meanings and edition; no numeric compatibility score is implied.
- The world is invented. Emotional, domestic, imagined biological and planetary jokes may coexist without requiring an astral database or tarot service.
- General type guidance never overwrites individual profile/history or current PostgreSQL eligibility. Unlisted future types remain unknown; NOT_RECOMMENDED visit guidance does not authorize cohabitation.
- The source was structurally checked; preparation, indexing and retrieval are not implemented. PY-011 will parse JSON deliberately and preserve pair identity/conditions, not apply the Markdown splitter to it.

### 4.2 Previously proposed physical trigger exercises

The following remain optional examples of physical/contextual questions, not the agreed storage schema and not a replacement for the accepted free-text trigger/experience field. Distinguish explicit constraints from preferences when search behavior is designed later.

| Proposed category | Example exposure | Question to resolve |
| --- | --- | --- |
| Moisture | Humid room, splashes, prolonged immersion | Which exposure is restricted, and on what evidence? |
| Cleaning products | Acidic cleaners | Which material and cleaning context does the source cover? |
| Impact and fragility | Falls, unstable display position | Is the restriction type-level or specific to this specimen? |
| Handling | Frequent touching or access by young children | Are sharp edges or vulnerable structures actually documented? |
| Care effort | Occasional dusting only | Does the available guidance fit the user's stated effort? |

Do not flatten nuanced geological evidence into unconditional claims, and do not manufacture profile observations for every type to fill the database. An authored fictional fear is valid within the game world even without a physical basis; explain it as a profile observation rather than forcing a scientific justification.

### 4.3 Separate tarot idea: deferred

The owner replaced the immediate astral compatibility catalog idea with a possible separate tarot-card divination program. Do not author that catalog, tarot cards or application now. PY-029 is a superseded local planning placeholder, not a pilot or tutorial dependency. Future scope needs a separate owner decision. Planetary jokes in the compatibility source do not change this boundary.

## 5. Assistant behavior

**Planned capabilities:**

1. Distinguish knowledge questions, catalog lookup, and combined recommendation requests.
2. Extract typed constraints and preferences from natural language.
3. Ask a clarifying question when missing or ambiguous information materially affects selection.
4. Route purely structured requests to PostgreSQL; apply explicit constraints as metadata filters in both lexical and vector branches for text-based retrieval. Recheck current state in PostgreSQL before recommendations.
5. Recommend only actual catalog specimens and validate referenced UUIDs.
6. Explain selection and comparisons using traceable source fragments and relevant specimen properties.
7. State when the catalog has no matching specimen or the corpus does not support an answer.
8. Offer explicit relaxation of soft preferences rather than pretending a hard constraint was satisfied.
9. Handle follow-up requests by retaining the relevant prior criteria and changing only what the user requests.
10. Distinguish supported facts, approximate editorial guidance, fictional personality, and unsupported statements.

## 6. Learning scenarios

These are **proposed exercises** to turn the direction into measurable increments:

| Request or situation | Learning objective |
| --- | --- |
| "How should I care for marble?" | Knowledge-only retrieval and source-based answering |
| "Which small stones do we have?" | Structured catalog tool without unnecessary vector search |
| "Find a small stone for a bathroom that tolerates my clumsiness." | Combine exact size, environmental knowledge, and fragility constraints |
| "Why this one rather than that one?" | Evidence-backed comparison of real candidates |
| "I want a beautiful stone with no care at all." | Clarification and realistic interpretation of care effort |
| "The same idea, but larger." | Stateful follow-up and incremental constraint changes |
| No suitable candidate exists | Empty results, uncertainty, and explicit preference relaxation |
| A Russian question over English documents | Cross-language retrieval and answer evaluation |
| Evidence is missing, conflicting, or qualified | Abstention and preservation of caveats |
| New individually registered stones arrive or case state changes | Index refresh and exclusion of stale availability |
| Documents or user text contain instructions to disregard application rules | Treat retrieved/user content as data; evaluate unwanted tool behavior and instruction following |

These scenarios do not authorize writes, adoption actions, or arbitrary tool execution by the assistant.

## 7. Framework and tooling learning goals

**Accepted targets:** LangChain and LangGraph are both part of the learning objective. Use local Ollama with the previously selected `langchain-ollama` integration and OpenRouter for comparisons across hosted models. Langfuse Cloud Hobby is the selected initial observability destination. Verify the actual installed stack before proposing implementation; add dependencies only when their increment starts. Provider integration packages, credentials, tracing SDKs, and live calls are not configured by this requirements update.

| Area | Proposed work |
| --- | --- |
| Model calls | Messages, prompt construction, parameters, structured output, timeouts, and error handling |
| LangChain retrieval | Documents, splitting, embeddings, retrievers, metadata filtering, and composing retrieval with generation |
| Embedding experiments | Compare section-aware versus size-based chunks, different embedding models, and query/document language behavior |
| Search | Compare keyword/text, vector, and hybrid approaches before assuming one is best; ranking and top-k are experiment variables |
| Tools | Narrow typed interfaces for catalog filtering, lookup by UUID, knowledge retrieval, trigger lookup, and candidate comparison |
| Tool correctness | Validate arguments, bound result sizes and tool calls, handle failures, inspect selected tools and arguments |
| LangGraph | Explicit state, routing, clarification, conditional edges, bounded retries, checkpoints, and resumption |
| Observability | Langfuse Cloud Hobby; trace retrieved fragments, tool calls, graph transitions, selection/exclusion decisions, model versions, latency, usage, cost, and errors |
| Harness | Repeatable dataset runs, versioned inputs/configuration, comparisons, and regression reports |

An illustrative graph is: understand request -> clarify if needed -> obtain constraints -> retrieve candidates and evidence -> verify suitability -> answer with sources. This is a teaching sketch, not a finalized graph specification.

Do not start with unrestricted model-generated SQL. Initial tools expose deliberate, bounded application operations. Deterministic filters must remain enforceable independently of the model's explanation.

### 7.1 Selected retrieval architecture

**Accepted, not implemented:** [ADR-0016](../adr/0016-typesense-lexical-qdrant-vector-experiments.md).

- PostgreSQL remains the authoritative operational store. Typesense supplies the initial lexical candidate branch; Qdrant supplies the initial vector branch.
- Generate embeddings explicitly in Python. Keep model identity, dimensions, metric, preprocessing, and source/index versions visible and reproducible.
- Feed both engines from a shared, versioned document representation with stable evidence IDs and parent stone/case/event/source references. Choose granularity explicitly; preserve source text and citations.
- Implement cross-engine hybrid retrieval in Python: parallel calls, separate candidate limits, deduplication, initial RRF fusion, and grouping of fragments into stone candidates. Do not sum incomparable raw scores.
- Evaluate an optional independent reranker after candidate union. Cross-encoder reranking and vector rescoring are distinct experiments.
- Verify final availability and shelter responsibility against PostgreSQL. Index metadata can narrow retrieval but cannot override current authoritative state.
- Provide rebuildable indexes. Explicit initial reindexing and later durable asynchronous delivery are separate increments; ADR-0004 governs transactional indexing intent when introduced. No distributed transaction between PostgreSQL and the search engines is assumed.
- Keep LangChain retriever/tool composition and LangGraph routing independent of the backend through narrowly useful adapters, not an unrequested universal storage framework.
- Begin with a fixed retrieval strategy inside a bounded search tool. Later compare agent-selected lexical/vector/hybrid strategies, query rewrites, decomposed questions, clarification, and repeated retrieval.
- Keep hard constraints deterministic and preserve unknown profile values. Do not let a model silently relax mandatory filters or turn historical states into current availability.
- Solr and pgvector are deferred. Optional vector/hybrid Typesense experiments reuse the same embeddings; they do not replace the initial Qdrant choice by implication.
- Do not install or configure any selected component as part of this documentation update.

## 8. Evaluation requirements and experiments

**After the first connected pilot:** evaluation is a core learning objective, not a prerequisite for the first result. No evaluation framework has been selected yet. **Accepted direction:** evaluation is part of the upcoming learning scope. The earlier deferral of free-form answer-quality work no longer excludes discussing and planning it; no evaluation tooling is installed by this document.

Begin with a small, manually reviewed set of approximately 10-15 questions as a **proposed starting size**, not a coverage claim. Record expected evidence, required facts, unacceptable claims, and expected selection/tool behavior where applicable. Establish the dataset before optimizing against it and retain cases for subsequent regression checks.

Evaluate these dimensions separately:

- **Retrieval:** did the relevant source sections appear, how highly, and how much irrelevant context was returned? Explore recall@k, precision@k, and ranking metrics when useful.
- **Selection:** do returned specimens exist and satisfy exact requirements? Are known environmental restrictions respected?
- **Answer correctness and completeness:** are necessary facts present and supported by reviewed expectations?
- **Grounding and citations:** does the explanation follow the retrieved evidence, and do citations actually support the associated claims?
- **Uncertainty:** does the assistant avoid inventing answers, candidates, or missing safety properties?
- **Tools and workflow:** correct tool, arguments, bounded execution, useful clarification, and sensible recovery from failures.
- **Operational behavior:** latency, model/tool calls, context size, failures, and reproducibility.

**Proposed baselines and comparisons:**

1. General-purpose model without the encyclopedia.
2. General-purpose model with the full encyclopedia as context, if it fits the chosen model and runtime.
3. General-purpose model with RAG.
4. Domain-tuned model without retrieval and with the same RAG, if practical.
5. General-purpose versus domain-specific embedding retrieval using the same dataset.

The corpus is small; a full-context baseline may be competitive. Measure rather than manufacturing a need for retrieval or agents.

Use deterministic checks for IDs, exact filters, schema validity, and other objectively testable properties. Human-reviewed examples are the initial reference for free-form quality. LLM-as-judge is a later experiment and must be calibrated against human judgment; it is not an infallible oracle. Langfuse Cloud Hobby is selected for observability and linking experiment results; LangSmith was considered but is not selected for initial setup. Hypothesis remains a future option, not a current dependency.

### 8.1 Providers and experiment identity

**Accepted direction; not implemented:**

- Support both local Ollama and OpenRouter in model experiments rather than assuming one fixed model or provider.
- Identify the provider, requested model, and actual serving model/provider where returned. Record provider request/generation IDs for later usage reconciliation when available.
- Read OpenRouter credentials from `OPENROUTER_API_KEY` in local environment configuration. Never record the key or authorization headers in the repository, datasets, logs, traces, or result files.
- Assign an experiment ID, dataset version, case ID, repetition, and attempt number. Link them to the application revision, prompt version, corpus/index version, retrieval configuration, and trace ID.
- Before an experiment, display the selected models, dataset cases, repetitions, evaluation strategy, configured limits, and estimated cost when an estimate is available. Do not run paid calls as an incidental side effect of tests or documentation commands.

### 8.2 Token and cost accounting

For each generation or embedding call, capture the following when available:

| Field | Meaning |
| --- | --- |
| Experiment, case, stage, attempt | Attribution to a specific run and purpose |
| Provider and model | Identity needed for comparisons and pricing |
| Input/output tokens | Provider-reported usage; preserve cached or reasoning-token breakdowns if supplied without double-counting totals |
| Usage provenance | Provider-reported, locally measured, estimated, or unavailable |
| Cost and currency | Provider-reported charge or an explicitly labeled estimate, with pricing source/date when calculated |
| Duration and outcome | Elapsed time, success, error, timeout, cancellation, or budget stop |
| Trace and provider request IDs | Links for inspection and reconciliation |

- Include interpretation, routing, query rewriting, generation, retries, and LLM-as-judge calls; do not count only the final answer.
- Report corpus-ingestion embeddings and per-query embeddings separately. Keep generation and judge costs separately visible even when reporting a combined total.
- Prefer provider-returned usage to word counts or fixed characters-per-token heuristics. Use model-appropriate token estimates for admission checks where available, then reconcile with actual usage.
- Do not present missing usage or cost as zero. Failed, timed-out, or cancelled requests may still incur provider charges; preserve identifiers and uncertainty.
- Ollama has no provider token charge in this setup; record tokens and elapsed time. Local compute is not declared economically free, and its monetary cost is not fabricated.
- OpenRouter model prices and serving choices can vary; use response/billing evidence when available and label locally calculated costs as estimates.
- Langfuse ingestion units are separate from model tokens and provider charges. A free observability plan does not make model inference or judge calls free.

### 8.3 Budget enforcement

**Planned capability:** configure budgets explicitly rather than hard-coding a spending amount in this document.

| Scope | Limits to support |
| --- | --- |
| One case/assistant execution | Model calls, tool calls, retries, input/context size, output tokens, elapsed time, and paid-call expenditure |
| Entire experiment | Cases, models, repetitions, aggregate tokens, elapsed time, and monetary spend |
| Evaluation stage | Separate judge-call/token/cost allowance so evaluation cannot silently consume the generation budget |

- The experiment runner checks available budget before each additional call and uses provider-supported output limits, timeouts, and bounded graph loops.
- Reserve capacity for pending/in-flight work and account for retries. Parallel execution must not independently spend the same remaining allowance.
- Stop scheduling new work when a limit is reached. Record `budget_exhausted` or an equivalent explicit outcome; do not score a non-executed or incomplete case as an incorrect model answer.
- A local estimate and provider request limits reduce exposure but do not promise an exact billing ceiling. Reconcile actual charges when possible and use a conservative reserve.
- Keep `make check` free of live paid or local-model inference. Define separately invoked live smoke checks and full dataset experiments. Ordinary backend tests remain deterministic and independent of provider availability.
- Begin by collecting the real statistics of one model call, then add accounting and limits incrementally. Exact starting amounts, model lists, concurrency, and token caps remain open.

### 8.4 Langfuse Cloud Hobby and trace structure

**Accepted choice, not connected:** use Langfuse Cloud Hobby as the initial LLM observability UI. Its published plan on 2026-10-29 was free without a credit card, with 50,000 ingestion units/month, 30 days of data access, and two users. Recheck [current pricing](https://langfuse.com/pricing) before setup; do not interpret units as tokens or assume permanent retention. Self-hosting or a paid upgrade is a later decision, not required now.

- One assistant turn or evaluation case has one root trace. Group related conversational turns by session/conversation ID; a graph thread/checkpoint identifier is a separate recorded identity when used.
- Trace the same logical stages whether generation is served locally by Ollama or through OpenRouter. Provider-side logging alone is not a trace of retrieval, catalog filtering, or graph decisions.
- Use LangChain/LangGraph callbacks for supported framework activity and explicit application observations for the decisions those callbacks cannot describe.
- Capture all cases in initial controlled learning experiments. Later sampling or cloud-volume management must preserve the ability to interpret a reported evaluation result.

| Observation | Required diagnostic information |
| --- | --- |
| Interpret request | Extracted hard constraints, soft preferences, unresolved ambiguity, and clarification outcome |
| Retrieve knowledge | Search query, metadata filters, retrieved chunk IDs, source/section, corpus/index version, retrieval/reranking scores and score meaning |
| Catalog lookup | Typed filter arguments, returned candidate UUIDs, result counts and any truncation |
| Candidate verification | Included/excluded candidates, stable reason codes, constraint checks, and supporting evidence IDs |
| Tool call | Tool name, validated arguments, bounded result, duration, attempt, and error |
| Graph execution | Executed node, chosen branch, observable routing condition, relevant state changes, retries and checkpoint references |
| Generation | Provider/model, prompt version, deliberately captured input/context and output, tokens, cost and duration |
| Evaluation | Rubric/evaluator version, reference evidence, score, explanation, judge identity/usage, and human feedback when available |

Example of a desired application-level selection record, not an implemented schema:

```json
{
  "stone_id": "<UUID>",
  "decision": "excluded",
  "reason_code": "MOISTURE_CONSTRAINT",
  "evidence_ids": ["marble-care-03"]
}
```

The record must reflect an actual executed constraint check and actual source evidence. Model-written justifications are not accepted as proof that the check happened. Observability captures execution, inputs, outputs, and explicit evidence; it does not reveal hidden model reasoning.

### 8.5 Persistence, logs, and data handling

- Keep structured application logs correlated by trace ID, alongside the Langfuse view. Record experiment and case IDs for evaluation-related events.
- Persist versioned experiment configuration, dataset identity, per-case results, aggregate usage/cost, and trace references locally for long-term Python/Spring AI comparison. Do not rely solely on Hobby's hosted history window.
- Hosted tracing transmits captured prompts, retrieved context, tool data, and responses to Langfuse. Select content capture deliberately, exclude credentials and authorization headers, and mask sensitive content where relevant.
- Langfuse dashboards and alerts provide inspection; budget enforcement must run locally before additional calls and must not depend on delayed telemetry exports.
- Avoid duplicate tracing/export paths that double-count a model invocation. Reconcile logical call IDs when multiple instrumentation layers are present.
- Langfuse account/project creation, region selection, credential configuration, SDK installation, external exports, dashboard setup, and any paid-plan upgrade remain unperformed. No connectivity is enabled by documenting these requirements.

Implementation references: [LangChain/LangGraph callbacks](https://langfuse.com/integrations/frameworks/langchain), [usage and cost tracking](https://langfuse.com/docs/observability/features/token-and-cost-tracking), and [Spring AI through OpenTelemetry](https://langfuse.com/integrations/frameworks/spring-ai).

### 8.6 Retrieval and agent experiment matrix

**Accepted experiment plan; implementation pending.** Introduce one controlled change at a time and retain baselines rather than enabling every feature at once.

| Experiment | Compare | Evidence to record |
| --- | --- | --- |
| Baselines | Structured SQL where applicable; direct model; full-context answer when the source set fits | Correctness, unsupported claims, constraints, context size, usage, latency |
| Lexical versus semantic | Typesense lexical and Qdrant vectors over the same evidence units | Relevant fragments/candidates found and missed, ranks, score meanings, query class |
| Cross-engine hybrid | Independent branches versus Python RRF fusion | Marginal recall, deduplication, grouping, per-branch contribution |
| Fusion configuration | Candidate limits, branch weights, RRF and explicitly designed alternatives | Held-out relevance, sensitivity, latency, config version |
| Reranker | Hybrid output before and after a separate reranker | Ranking improvement, added time/cost, truncation and missed candidates |
| Representations | Chunking, embedding models, query/document language, later multiple vector representations | Corpus/model versions, relevance, citation precision, resource cost |
| Orchestration | Fixed RAG versus bounded agent-selected tools/strategies and additional searches | Tool/argument correctness, useful extra calls, clarification, loops, final quality |
| Source combination | Operational profiles/history, Markdown encyclopedia and authored JSON type compatibility | Attribution, conflicting/unknown evidence, source routing, grounded explanation |
| Failure and freshness | Healthy branches versus timeouts/unavailability, stale metadata, new history, partially refreshed indexes | Bounded fallback, current-state verification, missing evidence, recovery traces |
| Optional engine comparison | Typesense vector-only and built-in hybrid versus Qdrant vectors plus Python hybrid | Same vectors/IDs/filters where supported; differences in backend and fusion behavior recorded separately |
| Later backend extension | pgvector or Solr only for a concrete additional question | Incremental learning benefit and cost, not technology count |

Comparison controls:

- Hold documents/chunks, source snapshot, IDs, query set, embeddings, metric, filters, and evaluation judgments constant when changing a backend. Record any unavoidable mismatch. Hold prompts and generation settings constant when evaluating retrieval effects.
- Exact nearest-neighbor results with equal inputs should agree apart from ties and numeric differences. ANN neighbor recall against exact search is a different measure from human-judged semantic relevance.
- Engine-level studies may vary ANN settings, selective filters, quantization, updates, latency distributions, memory, and multiple vector representations. They do not establish that an engine understands text better.
- Ten authored stones exercise correctness and end-to-end behavior, not scalability. Expand the corpus for ANN/performance studies; add meaningful distractors and difficult queries for relevance studies.
- Label expected fragments and suitable/unsuitable candidates separately. Report fragment-level versus stone-level metrics explicitly. Tune on a development set and retain held-out cases.
- Track recall/precision/ranking metrics as appropriate, hard-constraint violations, grounding/citations, uncertainty, tool calls, useful repeated retrieval, failures, latency, tokens, and monetary cost.
- Preserve lexical/vector result IDs, ranks and score meaning, fusion output, reranker output, candidate exclusions, graph branches, experiment configuration, budgets, and Langfuse trace references.
- Keep live inference and judge experiments separately invoked and budgeted; do not make make check depend on model providers or paid calls. Human-reviewed expectations precede calibrated LLM-as-judge experiments.
- For the later Spring AI implementation, reuse the same corpus, vectors where practical, questions, judgments, and behavior. A VectorStore adapter does not automatically expose a search engine's complete lexical/hybrid API.

## 9. Domain-model research candidates

These were explored in discussion and are **not selected dependencies or validated recommendations**:

- [GeoLLM-Qwen3.5-4B](https://huggingface.co/AshkanTaghipour/GeoLLM-Qwen3.5-4B): candidate for a domain-tuned generation comparison.
- [GeoGPT-R1-Preview](https://huggingface.co/GeoGPT-Research-Project/GeoGPT-R1-Preview): larger research candidate.
- [GeoEmbedding](https://huggingface.co/GeoGPT-Research-Project/GeoEmbedding): candidate for domain-specific retrieval comparison.
- Mineral photo classification is a possible separate experiment; mineral classes are not interchangeable with our rock-type taxonomy.

Before downloading or integrating a candidate, verify its current model card, language support, evaluation evidence, license, memory requirements, and compatibility with the chosen runtime. Domain fine-tuning is not assumed to improve our tasks. Model experiments do not replace the curated corpus or catalog truth.

## 10. Later Spring AI comparison

**Accepted direction:** implement the same RAG behavior later using Spring AI. Hold the corpus and catalog snapshot, evaluation questions and rubrics, generation and embedding models, chunking, retrieval parameters, and behavioral requirements constant where practical.

Compare integration effort, orchestration, context handling, tools, observability, and measured results. Record unavoidable differences. Python and Java implementations do not have to share an identical internal graph structure to be compared meaningfully.

## 11. Current progression and deferred work

The complete dependency map and per-ticket OpenSpec links live in [the delivery plan](../search/pilot-delivery-plan.md).

1. Review the existing stone JSON and encyclopedia; use the complete authored JSON compatibility guide (PY-027/PY-028); tarot is deferred.
2. Finish source-to-evidence preparation (PY-011), reusing published models and encyclopedia splitting. Typesense connection work is delivered (PY-012).
3. Index Typesense, add lexical and typed PostgreSQL retrieval (PY-013/PY-014).
4. Embed through one selected LangChain integration and index/query Qdrant (PY-015/PY-016).
5. Combine branches with RRF, group evidence and recheck current state in PostgreSQL (PY-018).
6. Connect one tool-capable model, minimum Langfuse tracing and bounded answer composition (PY-019/PY-020).
7. Add actual LLM tool routing in LangGraph and a minimal HTTP entrypoint; demonstrate the connected pilot (PY-022/PY-030).
8. Establish the measured baseline/evaluation harness (PY-017), then reranking, richer graph behavior, provider accounting, source mutations/freshness, representation/language/backend studies and Spring AI (PY-021, PY-019/PY-022 follow-ups, PY-006, PY-023–PY-026).

Full CRUD, UI, photos, Redis, Kafka, true token streaming, broad negative-path matrices and production infrastructure remain outside the pilot. PY-005 deletion is superseded; PY-004 public reads are optional, not required for SQL tools. Mutation semantics need their own reviewed contract and must not revive historical replay or batch creation.

PY-010 supplies real graph rollback and PY-007 supplies isolated migration verification. The dedicated independent-UoW isolation check remains unverified; do not conflate it with graph rollback or mark every historical deferred test complete.

## 12. Collaboration agreement

- The owner writes application code and learns syntax and frameworks hands-on; explain at an experienced Java engineer/architect level.
- Show code and explain it when requested, but do not edit application code unless explicitly asked.
- Documentation, imports of reference material, Git operations, scaffolding, and tooling changes may be delegated explicitly.
- Check the actual project stack and existing files before implementation advice.
- Prefer informative end-to-end backend scenarios over a new test for every field, framework setting, or intermediate coding step.
- Keep repository artifacts and code comments in English.
- Record accepted decisions separately from hypotheses and wishes. An ADR does not implement a feature.
