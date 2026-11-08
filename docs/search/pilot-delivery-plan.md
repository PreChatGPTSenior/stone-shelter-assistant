# Search learning delivery plan and OpenSpec task map

Updated: 2026-11-08. Authority: [ADR-0017](../adr/0017-source-first-tool-routed-pilot.md), [manifesto](../project-manifesto.md), [domain contract](../domain/model.md). THIS IS A LEARNING PROJECT: HAPPY PATH FIRST, THEN MEASURE AND IMPROVE.

## Reading this plan

The numbered order below is the work sequence, not numeric ticket order. Existing GitHub issue IDs are retained. PY-027 through PY-030 are **local proposed planning identifiers only**, not created GitHub tickets or issue numbers. Confirm/reserve their ticket IDs when publishing to the board; rename the local changes if those IDs have since been used. GitHub and the board were read, not changed in this documentation pass.

Each linked OpenSpec change contains proposal.md, design.md, tasks.md and capability requirements/scenarios under specs/. The presence of these artifacts is not implementation completion. Only evidence-backed pre-existing PY-011/PY-012 work is checked; future tasks remain unchecked. Post-pilot changes are documented backlog, not an instruction to apply every change now. Broader PY-019/PY-022 tickets have separate pilot and later checklists.

## Execution order

| Order | Ticket | OpenSpec task | Phase | Dependencies | Remote tracking |
| --- | --- | --- | --- | --- | --- |
| 1 | PY-027 | [Prepare the operational corpus and encyclopedia for the pilot](../../openspec/changes/py-027-pilot-source-corpus/proposal.md) | First: source preparation | PY-010 (delivered); coordinate with PY-028 | Local proposal; GitHub issue not created |
| 2 | PY-028 | [Fictional compatibility JSON (authored locally)](../../openspec/changes/py-028-type-compatibility-source/proposal.md) | First: source preparation | Existing StoneType vocabulary; coordinate with PY-027 | Local proposal; GitHub issue not created |
| 3 | PY-011 | [Prepare shared source evidence](../../openspec/changes/py-011-search-documents-and-scenarios/proposal.md) | Preparation | Sources prepared in PY-027/PY-028 | [#14](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14) |
| 4 | PY-012 | [Typesense connection (implemented locally)](../../openspec/changes/py-012-typesense-infrastructure/proposal.md) | Existing foundation; do not redo | No corpus dependency for connection work | [#15](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/15) |
| 5 | PY-013 | [Create Typesense collections and index prepared evidence](../../openspec/changes/py-013-typesense-indexing/proposal.md) | Pilot: indexing | PY-011 and PY-012; source corpus PY-027/PY-028 | [#16](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/16) |
| 6 | PY-014 | [Retrieve lexical evidence and exact PostgreSQL candidates](../../openspec/changes/py-014-lexical-and-structured-retrieval/proposal.md) | Pilot: retrieval | PY-013 | [#17](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/17) |
| 7 | PY-015 | [Generate document and query embeddings through LangChain](../../openspec/changes/py-015-langchain-embeddings/proposal.md) | Pilot: embeddings | PY-011 and prepared corpus; independent of Typesense availability | [#18](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/18) |
| 8 | PY-016 | [Connect Qdrant, index vectors and retrieve semantic evidence](../../openspec/changes/py-016-qdrant-semantic-retrieval/proposal.md) | Pilot: vector retrieval | PY-011 and PY-015 | [#19](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/19) |
| 9 | PY-018 | [Fuse lexical and vector evidence and verify current candidates](../../openspec/changes/py-018-hybrid-retrieval/proposal.md) | Pilot: hybrid retrieval | PY-014 and PY-016; PY-017 is not a dependency | [#21](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/21) |
| 10 | PY-019 | [Connect generation providers, Langfuse and experiment accounting](../../openspec/changes/py-019-providers-tracing-and-budgets/proposal.md) | Pilot slice, then post-pilot extension | PY-015 for embedding observations; retrieval operations for the connected trace | [#22](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/22) |
| 11 | PY-020 | [Compose evidence-grounded answers through LangChain](../../openspec/changes/py-020-grounded-answer-composition/proposal.md) | Pilot: answer composition | PY-018 and the PY-019 pilot slice | [#23](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/23) |
| 12 | PY-022 | [Build a bounded LangGraph with real LLM tool selection](../../openspec/changes/py-022-tool-routed-langgraph/proposal.md) | Pilot slice, then post-pilot extension | PY-014, PY-018, PY-019 pilot and reusable answer composition from PY-020 | [#25](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/25) |
| 13 | PY-030 | [Expose and verify the connected search assistant pilot](../../openspec/changes/py-030-connected-search-pilot/proposal.md) | Pilot: final connected result | PY-020 and PY-022 pilot slices; PY-019 tracing; prepared source corpus | Local proposal; GitHub issue not created |
| 14 | PY-017 | [Establish the baseline and incremental evaluation harness](../../openspec/changes/py-017-retrieval-and-answer-evaluation/proposal.md) | After the connected pilot | PY-030; retrieval and trace outputs; PY-019 budgets for live runs | [#20](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/20) |
| 15 | PY-021 | [Measure a separate reranking stage](../../openspec/changes/py-021-reranking-experiment/proposal.md) | After the connected pilot | PY-017, PY-018 and PY-019 accounting | [#24](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/24) |
| 16 | PY-024 | [Compare representations, embeddings and query languages](../../openspec/changes/py-024-representation-and-language-experiments/proposal.md) | After the connected pilot | PY-017 and PY-019; use source corpus from PY-027/PY-028 | [#27](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/27) |
| 17 | PY-006 | [Define source updates and append history for later retrieval experiments](../../openspec/changes/py-006-source-mutations-and-new-evidence/proposal.md) | After the connected pilot | PY-010 current contract; PY-017 for measuring new evidence; PY-023 for later automatic refresh | [#6](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/6) |
| 18 | PY-023 | [Add durable indexing intent and measured freshness recovery](../../openspec/changes/py-023-durable-indexing-and-freshness/proposal.md) | After the connected pilot | PY-018/PY-017; PY-006 only for mutation-specific scenarios | [#26](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/26) |
| 19 | PY-025 | [Compare Typesense vectors and built-in hybrid with the initial pipeline](../../openspec/changes/py-025-typesense-vector-comparison/proposal.md) | After the connected pilot | PY-017 and PY-018; same embedding assets from PY-015 | [#28](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/28) |
| 20 | PY-026 | [Reproduce measured Python behavior with Spring AI](../../openspec/changes/py-026-spring-ai-comparison/proposal.md) | After the measured Python baseline | PY-017; PY-020/PY-022 behavior and shared experiment assets | [#29](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/29) |
| 21 | PY-004 | [Provide optional catalog inspection endpoints](../../openspec/changes/py-004-optional-catalog-reads/proposal.md) | Deferred product convenience; not a pilot prerequisite | Existing registration; reuse appropriate typed queries from PY-014 if available | [#4](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/4) |

Source preparation comes first: review the existing ten stone requests and encyclopedia, use the authored fictional compatibility JSON, and inventory them together. These tasks create input material, not relevance judgments. PY-011 then produces concrete indexable evidence for all families. Infrastructure already written for PY-012 is reused, not reimplemented.

PY-015 needs prepared evidence, not a running Typesense index. PY-016 is likewise independent of Typesense infrastructure. The table is a convenient learning order, not an unnecessary technical dependency. PY-017 does not block hybrid search, RAG or the graph. PY-006 only gates mutation-specific freshness experiments. PY-023 is deferred beyond the pilot and requires an explicit future scope decision; no queue, outbox or automatic recovery is needed for the happy-path exercise. PY-004 is optional inspection and never gates tool SQL lookup.

## Superseded separate idea

PY-029's former immediate astral-source proposal is superseded by a separate future tarot program. It is deferred, not implemented, and has no dependency in this plan. Its [local planning record](../../openspec/changes/py-029-astral-compatibility-source/proposal.md) remains for context. ADR-0018 supersedes the earlier ADR-0017 source count and Markdown-only assumption.

## Authored compatibility source

[The English JSON guide](../../stone-rules/type-compatibility/stone-type-compatibility_en.json) now covers all ten enum types and all 55 unordered pairings (45 mixed-type and ten same-type). It is fictional provider-style reference data, not registered pets or a search index. PY-028 source authoring is complete locally; PY-011 JSON parsing/projection is not implemented. One-off checks verified JSON parsing, enum coverage, unique IDs and pair completeness. No application checks or indexing ran for source authoring.

## First connected result

A question enters a minimal HTTP endpoint, a real tool-capable LLM chooses typed operations, LangGraph executes the bounded path, and LangChain composes an answer from retrieved evidence. Trace the chosen tools and arguments, evidence, final PostgreSQL checks, model configuration, usage when available and output in Langfuse. Do not claim access to hidden model reasoning.

Required supported examples:

1. Exact type/size request uses PostgreSQL; no pointless lexical/vector calls.
2. A preference-based adoption request uses Typesense and Qdrant with common hard filters, RRF, stone grouping and final PostgreSQL eligibility/current-shelter checks.
3. Reference questions retrieve and cite the Markdown encyclopedia and fictional JSON type-compatibility guide, with their meanings kept distinct. Not every question needs every source or backend.
4. A combined candidate/reference explanation uses real candidate identities, actual supporting passages and explicit unknowns rather than invented profile facts.

The model selects application tools: exact lookup, hybrid search, reference search with source-family selection, and details/history lookup. Initially the hybrid tool deterministically invokes both engines. Model selection between lexical/vector/hybrid strategies is a later PY-022 experiment.

Ordinary verification uses real Testcontainers backends with controlled embedding/model outputs. Real inference is a separate explicitly invoked demonstration with a selected provider/model and finite limits. Do not mark the pilot complete based only on mocked routing or a schema-valid response. No full UI, streaming, Redis, product CRUD, durable indexing worker or full evaluation harness is required.

## Measured improvement after the pilot

PY-017 owns the small human-reviewed dataset, per-case outputs, metrics and baseline configuration. Retrieval relevance, candidate suitability, tool correctness and answer grounding are separate measurements. Eval framework selection remains open; no package named “EVIL” is selected by the earlier spoken description.

Keep corpus snapshots and JSONL result files, when useful, in separate experiment tooling rather than application intermediates. Use the same corpus/configuration when attributing changes to reranking, embeddings, chunking, language, backend or agent strategy. PY-019 extends token/cost accounting to all stages, with separate judge budgets and local caps. Missing usage or cost stays unknown.

The compatibility JSON is already authored. A separate tarot idea is deferred and excluded from these prerequisites. The later source-update/history exercise remains PY-006, and automatic cross-index delivery/freshness remains PY-023. Hypothesis, negative-path matrices and more infrastructure are optional later learning exercises, not newly required dependencies.

## Code audit and implementation evidence

Read-only audit on 2026-11-08; no application tests, provider calls or database access were performed for this plan.

| Evidence inspected | What exists | What is still missing |
| --- | --- | --- |
| pyproject.toml | Async SQLAlchemy/PostgreSQL, FastAPI/Pydantic, langchain-text-splitters, typesense, pytest/pytest-asyncio/Testcontainers | Generation/embedding LangChain integrations, LangGraph, Qdrant client, Langfuse |
| catalog/adoption persistence models; application/register_stone.py | Required lifetime case, optional profile, events and source-owned state saved as one ORM graph | Partial update/event append operations |
| catalog/persistence/repository.py | add() registers the graph in the session | Exact lookup, candidate hydration and search read queries |
| fixtures/stones; fixtures/shelters.json; tools/load_stones.py | Ten stone requests, two shelters, explicit HTTP loader | No new operational data generation required just to repeat existing examples |
| search/documents.py; search/enums.py | Four Pydantic evidence kinds and provenance/version fields | Operational preparation and new reference-family representation |
| search/encyclopedia.py; unit/search/test_encyclopedia.py | MarkdownHeaderTextSplitter preparation of fourteen sections and a real-source test | Index integration and compatibility JSON preparation |
| Compose/settings/infrastructure/typesense.py/bootstrap/app.py | Typesense service, async SDK factory and lifespan ownership; Qdrant Compose service | Typesense collections/indexing/search; Qdrant Python client, lifecycle, collections and retrieval |
| integration/conftest.py; integration/search/test_typesense.py | Isolated PostgreSQL/Typesense containers and authenticated Typesense smoke test | Real retrieval and connected graph scenarios |
| source tree and accepted backlog | Registration path and prepared data foundation | Embeddings, Qdrant, RRF, tools, graph, answers, tracing, budgets and evaluation |

PY-012's existing checklist records a previous make check run with 43 passing tests; this audit did not repeat it or claim it verifies unimplemented retrieval. PY-011 and PY-012 implementation is included with the current feature branch for publication; GitHub ticket status must be updated separately. No board status is changed by marking an existing local implementation item in OpenSpec.

## Historical boundaries

PY-001/002/003/007/008/009/010 retain their delivered history and known deferred checks. No retroactive implementation changes or archives are created. PY-005 physical deletion is superseded and receives no new implementation spec. PY-004/PY-006 are included only as explicitly deferred work so they cannot reappear as hidden pilot prerequisites. The dedicated independent-UoW isolation check remains unverified; graph rollback is a different delivered scenario.
