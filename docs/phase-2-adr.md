# Фаза 2 ADR

Date: 2026-11-09

Status: The pilot HTTP route runs LangGraph with OpenRouter and Langfuse. Budget enforcement and cross-model evaluation are pending. The [Hybrid Search ADR](hybrid-search-adr.md) is implemented with locally verified end-to-end provenance; paid-model quality comparisons remain pending.

This document consolidates the discussion of the first agent-driven search workflow, mandatory LLM budget reservations, and end-to-end observability. It supplements [Architecture Decisions](adr.md). Implementation progress remains in [Task Log](task-log.md); this document does not mark planned behavior as complete.

## 1. Purpose and starting point

Build one visible, evidence-grounded workflow in the fictional pet-rock shelter. The owner writes application code while learning Python and AI frameworks. Keep components small and inspectable; establish the first working scenario before evaluating retrieval quality or adding production operations.

The handoff baseline is commit `12a9b9d`, with PY-035 completed and 49 tests reported passing. No tests were rerun during the design discussion.

Existing capabilities:

- Registration persists a stone, optional profile, lifetime shelter case, and supplied events in PostgreSQL.
- A stone card and each case event are separate documents in Typesense and Qdrant.
- Lexical and semantic retrieval cover stone cards, event notes, the encyclopedia, and the authored compatibility guide.
- PostgreSQL lookups return current status and shelter, complete case timelines, and stone details by internal or external ID.
- Exact compatibility lookup uses a symmetric `pair_key` in Typesense.
- Assistant tools already use LangChain `@tool` in `assistant/tools.py`.
- `/api/v1/questions` runs the pilot graph and returns a Langfuse trace ID.
- Local Ollama supplies embeddings. OpenRouter supplies the agent and answer models.

PostgreSQL remains authoritative for operational facts. Search indexes are projections. Current adoption status must never be reconstructed from historical events.

## 2. First end-to-end scenario

> I would like to adopt Madame Obsidian into a quiet home. I already have a granite stone. Would she be a suitable companion, and is she available now?

The supplied Madame Obsidian fixture has a profile describing a quiet, predictable home and an `AVAILABLE` status. It exercises identity retrieval, profile reading, exact pair knowledge, and current availability in one request.

Expected retrieval path:

1. `search_stones_lexical` finds Madame Obsidian by name.
2. `get_stone_details` reads her stone, optional profile, and current case from PostgreSQL.
3. `get_compatibility_pair` retrieves the authored rule for `OBSIDIAN` and `GRANITE`.
4. A mandatory graph step calls `get_current_stone_statuses` immediately before answer generation.
5. The answer explains suitability, relevant care constraints, compatibility, and checked availability with sources.

The current implementation uses the [Hybrid Search ADR](hybrid-search-adr.md). Named recommendations use lexical name search; general recommendations run one prepared hybrid operation. Named status, care and exact pair questions use their direct reference routes.

Velvet Slate's supplied status is RETURNED; neither its history nor its quiet-home profile establishes availability.

## 3. Current graph and retrieval

See the [current workflow diagram](phase-2-search-workflow-diagram.md).

The parser proposes criteria, English lexical/semantic queries and an optional candidate type referenced to an original fragment. Code grounds the candidate type and constructs AVAILABLE/en filters; the model cannot supply arbitrary exact filters. The ground_question evaluation-model stage verifies sensitive proposals against a complete versioned English concept/example catalog in Typesense; Python checks original quote bindings, never promotes unverified agreements, and blocks uncertain candidate-type filters. Lexical phrase rules are removed. The planner validates the route. The graph prepares one tool call without another search-model invocation: search_stones_hybrid for general matching, search_stones_lexical for named candidates. Hybrid search executes Typesense and Qdrant concurrently and counts as two backend calls against the four-call allowance.

RRF combines deduplicated engine ranks into a pool of at most ten. The selection model receives parsed criteria, the reference request, original source wording and retrieval provenance, then chooses up to three retrieved IDs. Missing parsed retrieval data stops general matching rather than reinterpreting the question. PostgreSQL card reads and current status verification follow selection. Candidate evaluation and response assembly retain their existing policy.

| Purpose | Tools |
| --- | --- |
| General candidate retrieval | search_stones_hybrid |
| Named candidate retrieval | search_stones_lexical |
| Stone details | get_stone_details |
| Current availability | get_current_stone_statuses / get_stone_status_by_name |
| Event-note retrieval | search_case_events_lexical / search_case_events_semantic |
| Complete case history | get_case_timeline |
| Reference retrieval | search_knowledge_lexical / search_knowledge_semantic |
| Exact type compatibility | get_compatibility_pair |

History tools exist but are not yet included in the reference planner. The twenty-case suite marks this capability boundary.

### Mandatory verification

Validate the selected IDs against actual search results. After loading the cards, invoke `get_current_stone_statuses` once for the candidates whose cards were found. The answer uses the checked statuses for current availability.

For the pilot, only a confirmed `AVAILABLE` status permits an adoption recommendation. Missing status does not establish eligibility. A result of `RESERVED`, `ADOPTED`, or `RETURNED` excludes the stone from adoption recommendations. Availability describes the time of the check; this workflow does not reserve or adopt stones.

### Answer and sources

Return a typed result containing answer text, recommended stone IDs, and sources. Preserve provenance:

- Profile and operational details: PostgreSQL record identity and stone ID.
- Compatibility and other indexed knowledge: evidence document ID, title, and `source_key`; retain the source path where available.
- Availability: the PostgreSQL status-check result for the candidate.

Distinguish authored fictional compatibility rules from geological reference information. Do not invent missing profile data or source content. Explain insufficient evidence when a supported answer cannot be formed.

Code validates that recommended IDs belong to checked, eligible candidates and cited IDs belong to evidence actually retrieved. This structural validation does not itself prove the semantic correctness of every sentence; free-form answer evaluation follows the first pilot.

### State and boundaries

State needs message history, a tool-call counter, candidates, evidence, checked statuses, budget outcomes, and correlation identifiers. The budget service owns shared balances and reservations. Expose the asynchronous graph through an assistant service behind `POST /api/v1/questions`. FastAPI lifespan opens the shared clients and session factory once. The questions, knowledge, and manual testing routes reuse those resources through the application. Keep test conversations to at most five turns.

## 4. Generation and embeddings

Use `ChatOpenRouter` from `langchain-openrouter` for generation, with an explicitly configured model supporting tool calling. Bind the existing LangChain tools through the adapter. Retain Ollama for embeddings used by semantic retrieval; embeddings are not generated through the chat model.

Record model identity, generation limits, prompt version, and pricing assumptions for the baseline. Ordinary tests must not call a paid model or depend on the local Ollama service.

## 5. Mandatory budget checks and reservations

The user clarified that reservation means reserving LLM spending capacity. Stone reservation is outside this workflow.

Use two spending limits in USD for each calendar month in UTC:

- The **application budget** covers all OpenRouter usage from the application.
- The **user budget** covers OpenRouter usage attributed to one application user across their questions. The server assigns `local-test-user` for the pilot.

Set the limits in server configuration. Apply one shared budget-controlled model wrapper to both `agent` and `answer`. Every OpenRouter call must pass through it. The skeleton's per-run budget is temporary and will be replaced by the two monthly limits for paid calls.

Track `limit`, `spent`, and `reserved` using `Decimal`. Both budgets must meet the admission condition:

```text
spent + reserved + reserve_amount <= limit
```

### Reservation lifecycle

1. Calculate the reservation from the complete input, including instructions, history, tool schemas, and tool results, plus the maximum permitted output. Include billable reasoning when applicable. Use the configured model and applicable tariff. A strict monetary ceiling requires a defensible upper bound on call cost.
2. Before sending each request to OpenRouter, check both monthly balances and record the reservation against both in one atomic operation. If either balance is insufficient, leave both unchanged. This prevents parallel requests from reserving the same available balance. The application makes this decision independently of the model.
3. On completion, use the actual cost reported by OpenRouter in `usage.cost` to settle the reservation and release unused capacity in both budgets. Record one charge attributed to both scopes, together with the `user_id`, `trace_id`, and OpenRouter generation ID when available.
4. If either budget cannot admit a call, stop with a deterministic result. Final answer generation follows the same reservation rule.
5. If a request was definitely not sent, release its reservation. If its outcome or charge is unknown, retain the reservation and stop the run. A timeout after sending does not prove that no charge occurred. Release or settle that reservation only after its outcome is established.

Reservations are internal application accounting. OpenRouter performs actual billing. The adapter must expose the cost and usage needed for settlement; verify this when integrating the selected adapter version. Unknown cost must not be silently treated as zero. If an actual charge exceeds the estimate, record the real cost and stop further spending rather than hiding the overrun.

The four-tool limit and the monetary budgets are independent controls. PostgreSQL and Redis are both candidates for storing spending and reservations. Choose the backend in a separate decision based on atomic updates across both budgets, durability, and recovery of unresolved reservations after a restart. The monthly accounting must persist across questions and process restarts.

## 6. Observability in the first pilot

Include Langfuse from the first working scenario, as selected in the main ADR. Trace the graph, model calls, tool calls, backend requests, budget decisions, status checks, and final validation.

### Identity and propagation

| Identifier | Scope |
| --- | --- |
| `user_id = "local-test-user"` | All requests from the single learning-project user |
| `eval_case_id` | Stable scenario label across evaluation runs |
| `fixture_version` | Version of the fixture data loaded for the run |
| `trace_id` | Complete handling of one question across the application stack |
| `span_id` | One operation within the trace |

A new question gets a new `trace_id`. Requests share the test `user_id`. Evaluation requests may supply the scenario and fixture labels as trace metadata. Conversation sessions are deferred.

Create a root trace for each questions request that invokes the assistant service. Propagate the same context through the graph, services, tools, and client operations. Add `trace_id` to structured application logs and include it in the pilot HTTP result.

Use the Langfuse LangChain/LangGraph callback for framework operations and explicit nested spans for budget operations and PostgreSQL, Typesense, Qdrant, and Ollama calls. These are client-side spans; visibility into a provider's or database server's internal execution is not implied.

### What to record

- Question, final result, model identity, prompt version, and run configuration.
- Model inputs, available tool schemas, tool results supplied to the model, and returned tool calls.
- Tool name, arguments, tool-call ID, result, duration, and errors.
- Retrieved evidence IDs and provenance; operational lookup identities and checked statuses.
- Graph transitions and their observable causes: tool requested, evidence complete, call limit reached, insufficient budget, mandatory verification, or validation failure.
- Token usage, actual cost, reservation amounts, settlement, and unresolved cost state.
- Final citation and recommendation validation outcomes.

This reconstructs observable decisions and evidence flow. A model-provided short explanation of its selection may be recorded as an explanation, not as a verified transcript of internal reasoning.

Example trace shape:

```text
question
├── agent
│   ├── budget.reserve
│   ├── llm
│   └── budget.settle
├── tool: search_stones_lexical
│   └── typesense.search
├── agent (...)
├── tool: get_stone_details
│   └── postgres.read
├── agent (...)
├── tool: get_compatibility_pair
│   └── typesense.lookup
├── verify
│   └── postgres.current_statuses
└── answer
    ├── budget.reserve
    ├── llm
    ├── budget.settle
    └── validate_sources_and_recommendations
```

Langfuse observes budget decisions. The budget component owns enforcement. The pilot uses the Langfuse endpoint configured by `LANGFUSE_BASE_URL`. Budget admission currently allows every model call.

## 7. Manual verification, tests, and evaluation

Prepare the development dataset through three separate POST requests. Use the existing knowledge endpoints to replace the encyclopedia and compatibility guide independently, then use the local testing router to replace the operational fixture data:

1. `/api/v1/knowledge/encyclopedia/reindex` replaces encyclopedia documents in Typesense and Qdrant.
2. `/api/v1/knowledge/compatibility/reindex` replaces compatibility documents in both indexes.
3. `/api/v1/testing/normalize-data` replaces shelters, stones, profiles, cases, and events in PostgreSQL and rebuilds the `stones` collections in Typesense and Qdrant. The POST request starts the reset immediately.

Send the Madame Obsidian question to `POST /api/v1/testing/manual-test` for a deterministic baseline. It runs the three existing tools and returns the name search hit, PostgreSQL card with status, and compatibility rule with granite. Use the same question at `POST /api/v1/questions` with `openrouter/free` to inspect the answer, sources, tool sequence, PostgreSQL status check, and Langfuse trace. Explicitly authorized, opt-in paid model comparisons may replay a frozen assessment case with bounded output tokens while budget admission remains a stub. Reservation behavior is evaluated when enforcement is implemented.

### Conditional pair decisions

Conditional pair eligibility is computed from author-defined mandatory conditions and typed household facts. A model-supplied rule quotation and household fragment ID cannot confirm accommodations. The current model assessment DTO contains character and individual-compatibility evidence only. The application and active replay accept only the current DTO; obsolete accommodation fields are rejected. Past experiment files are reference records, not supported input formats.

Each authored condition has an ID, fact type, expected boolean, and verbatim rule quotation. The initial granite–granite annotation requires both `decision_rotation_agreed` and `decision_deadline_agreed`. `parse_question` extracts established agreements or explicit denials as typed facts, and the graph restores their original question quotes from fragment IDs. A missing pair scope means a household-wide agreement. An explicit `applies_to_pair` restricts a fact to that unordered pair, preserving repeated types.

All mandatory conditions must be marked and confirmed. Missing facts, denials, conflicting values, invalid rule quotations, duplicate condition IDs, and facts scoped to another pair cannot confirm the rule. Existing documents without condition annotations remain conditional. Per-condition results and supporting facts are recorded with each candidate reason. The graph renders “Условия не подтверждены.” for unconfirmed or unmarked conditional rules. Reindex compatibility knowledge after reviewing the updated fixture to make the annotation available to live runs. The policy version is `candidate-evaluation-v4`.

### Frozen model-assessment records

Archive model-evaluation inputs and results under `tests/fixtures/agent-eval/<case>/`. Each case stores the exact input messages, DTO schema, parsed criteria, recorded cards and statuses, source evidence, fixture version, source trace/observation IDs, and input SHA-256. Versioned run records store requested model and reasoning settings, output allowance, returned DTOs, validation and scenario checks, reported token usage, elapsed time, cost, and Langfuse links. Retain unsuccessful attempts and record retries explicitly.

Schema validity and semantic correctness are separate checks. Preserve expected facts and source-grounding requirements independently of model outputs. A frozen replay compares the same assessment input across models and does not re-run search or question parsing. Keep recorded past runs identifiable as past experiments. During stabilization, update active fixtures and tests directly to the current prompt and DTO. Do not implement old-format adapters or preserve obsolete schema tests.

The first [quiet-home assessment archive](../tests/fixtures/agent-eval/quiet-home-with-granite/README.md) records five paid models and Dots at an 8192-token output allowance. All six completed DTOs after one Dots provider-error retry. Terra and Gemini passed the scenario checks. The archive documents the remaining source-grounding and accommodation errors. The current test continues to read its original fixture path until a separately authorized Python change relocates that reference.

### DeepEval on full questions runs

DeepEval belongs to the optional `eval` dependency group. It runs in the opt-in test process after the HTTP question completes. The application graph owns condition enforcement, source validation, and candidate decisions. G-Eval scores semantic character-evidence support with a separate Terra judge, a 4096-token allowance, medium reasoning, and an initial threshold of 0.8. Judge calls and reported costs remain identifiable separately from the assessed model.

The question contract accepts `evaluation_max_tokens` and `evaluation_reasoning_effort`. Assessment defaults are 8192 output tokens and medium reasoning, with a per-request high override for the selected DeepSeek model. Other stage token caps remain separate. Common model construction leaves temperature unspecified to avoid forcing an unsupported parameter across providers. The evaluated models use strict JSON Schema.

Store end-to-end HTTP comparisons separately from fixed-input model replays, since parsing and candidate selection can vary. Publish recorded HTTP results to `PY-037/quiet-home-questions-v4` for experiment comparison, linking each record to its actual request trace. Score and archive failed upstream attempts explicitly. Exact source-reference and quotation checks accompany semantic judge scores.

The targeted [granite–granite Luna case](../tests/fixtures/agent-eval/quiet-home-granite-pair/README.md) verifies both authored conditions as `unknown` through the graph. It also exposed a G-Eval false positive for a source-reference error. Semantic judge approval cannot override failed identifier checks or graph decisions. Expanding or calibrating the judge rubric remains evaluation work.

Then add reproducible automated checks using authored fixtures, a controllable tool-calling model stub, controlled embeddings, and disposable Testcontainers. Populate only the temporary services needed by each test. Automated tests must never use the persistent development database.

| Scenario | Required observation |
| --- | --- |
| Madame Obsidian end to end | Tool calls consume real fixture-backed results; answer references retrieved evidence and a checked available candidate. |
| Stale search status | After indexing, change only test PostgreSQL status to `RESERVED`; mandatory verification excludes the stone even if the model omits a status call. |
| Retrieval call bound | A model stub requesting more tools cannot execute beyond four permitted calls. |
| Insufficient budget | A refusal by either monthly budget prevents the model call and leaves both balances unchanged. |
| Settlement | The OpenRouter charge counts toward both budgets and unused reserved capacity becomes available. |
| Shared monthly budgets | Decision calls, final answer generation, and later questions all use the applicable monthly balances. |
| Concurrent reservation | Parallel calls cannot reserve the same available capacity. |
| Unknown call outcome | Reservation remains held and further model execution stops. |
| Trace propagation | One question produces a root trace with correctly parented graph, tool, backend, and budget spans. |
| Evaluation correlation | Independent requests have distinct trace IDs and can share a scenario or fixture version. |

Use a test span collector for automated tracing checks. Run the relevant existing regression checks when implementation changes land.

Once the service passes its checks, evaluate answers from multiple real models on the same set of questions and project data. Record each model's configuration, answer, sources, trace ID, latency, and cost. Review whether claims are supported, recommendations reflect the checked status, and the service handles missing evidence and budget stops predictably. Use the traces to distinguish model decisions from retrieval and orchestration behavior. Record the results and resolve failures in those required behaviors before finalizing the API contract and streaming.

## 8. Delivery boundaries and later work

The backend phase focuses on the search workflow, budget admission and reservations, observability, traceability, and answer evaluation. Deliver the assistant service behind the pilot HTTP route with status verification, cited results, and tracing. Inspect real-data runs first, add automated checks second, and complete the answer evaluation across models third.

Use the minimal `/api/v1/questions` route to exercise the application and its dependencies. Finalize the HTTP contract and decide what to stream once the backend checks pass and the cross-model evaluation shows that answers are controlled.

After the first scenario works, add scenarios using semantic search, event notes, timelines, and encyclopedia material as needed. Compare retrieval, embeddings, chunks, lexical and semantic fusion, and reranking through controlled experiments after establishing a baseline.

Queues, automatic retries, distributed recovery, full CRUD/UI, production deployment, and broad negative-case matrices are deferred. So are stone reservation and adoption writes. Budget uncertainty handling and stale-status verification remain in scope because they enforce explicit pilot requirements.

Before each opt-in paid experiment, select the concrete models, tariff source, output limits, reasoning settings, and Langfuse destination, then record actual usage and cost. Monthly budget amounts, storage, and reservation upper-bound enforcement remain implementation work. Assign task IDs through the existing Task Log workflow when implementation scope is selected.

## 9. Reference documentation

Official documentation consulted during the discussion:

- [LangGraph workflows, agents, and ToolNode](https://docs.langchain.com/oss/python/langgraph/workflows-agents)
- [LangChain ChatOpenRouter integration](https://docs.langchain.com/oss/python/integrations/chat/openrouter)
- [OpenRouter tool calling](https://openrouter.ai/docs/guides/features/tool-calling)
- [OpenRouter usage accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)
- [Langfuse LangGraph integration](https://langfuse.com/integrations/frameworks/langgraph)
- [Langfuse user tracking](https://langfuse.com/docs/observability/features/users)
- [Langfuse sessions](https://langfuse.com/docs/observability/features/sessions)
