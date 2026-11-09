# Task Log

Select any item from **Backlog**. Discuss its scope, then move it to **Current** and assign the next unused `PY-NNN` ID. Backlog order is optional. Move a task to **Done** with the same ID once its result has been implemented and verified.

Completed entries summarize the work that landed. Existing IDs are reused where the history identifies them. `PY-027` and `PY-028` are retrospective IDs for maintenance work. Keep legacy GitHub IDs `PY-013` through `PY-026` reserved.

## Done

- [x] **PY-034 — Search reference knowledge in Typesense and Qdrant and look up exact pairs by pair key.** Add lexical and semantic search with shared filters and expose both searches and exact pair lookup as assistant tools. Verify encyclopedia results from both engines, reversed pair order, and a same-type pair using the authored fixtures in disposable containers. All 47 tests passed.
- [x] **PY-033 — Search case events in Typesense and Qdrant and read timelines from PostgreSQL.** Search event notes with shared filters for stone, event type, and date range. Expose both searches and chronological lookup by case ID as assistant tools. Verify that both searches return Velvet Slate's return note and PostgreSQL returns all five events in order in disposable containers. All 46 tests passed.
- [x] **PY-032 — Search stone cards in Typesense and Qdrant.** Add lexical and semantic search with shared exact filters, a PostgreSQL lookup for current adoption status and shelter, and three assistant tools. Verify that both searches return a registered fixture card and that the PostgreSQL lookup returns its case state in disposable containers. All 45 tests passed.
- [x] **PY-031 — Reload knowledge through explicit endpoints.** Index the encyclopedia and compatibility guide in one `knowledge` collection per engine. Each endpoint replaces its own source in Typesense and Qdrant. Verify 80 documents, exact pair filtering, and removal of obsolete documents in disposable containers. All 44 tests passed.
- [x] **PY-030 — Index stone profiles and case events on registration.** Build one stone card with the optional profile and one document per case event. Write them to the `stones` collection in Typesense and Qdrant. Verify both indexes through HTTP registration in disposable containers. All 43 tests passed.
- [x] **PY-029 — Parse the stone type compatibility guide.** Build 55 pair documents, ten type portraits, and one reading-rules document from the authored JSON fixture. Verify stone-type coverage, source provenance, and unique, stable document IDs.
- [x] **PY-028 — Rename the project and document its layout.** Align the repository, Python package, API, and local infrastructure on Stone Shelter Assistant. Recreate the environment, apply migrations to fresh storage, and pass all 42 tests. Add the repository organization guide and reference it from `AGENTS.md`.
- [x] **PY-027 — Simplify repository structure.** Replace OpenSpec with compact project documentation. Consolidate registration in `stones` and shared technical foundations in `core`. Move app assembly to the package root and add the placeholder questions route. Remove unused scaffolding, domain dataclasses, and one-off loaders. Split search into infrastructure, stones, and knowledge, share document helpers, and build one projection for both indexers. Require explicit loading of stone/profile relationships, move reference fixtures to `fixtures/knowledge`, and synchronize the environment template with Compose and the application.
- [x] **PY-012 — Set up local search and verify initial indexing.** Connect and test Typesense in a disposable container. Verify that one HTTP registration indexes the stone in Typesense and Qdrant using controlled embeddings.
- [x] **PY-011 — Prepare initial search evidence.** Split the English encyclopedia into fourteen search documents and author the fictional compatibility guide with ten rock types and 55 unordered pairs. This entry covers the groundwork that landed.
- [x] **PY-010 — Register a complete stone record.** Accept one stone with its shelter case, optional profile, and supplied events through HTTP.
- [x] **PY-009 — Prepare registration fixtures.** Add the registration contracts and ten authored JSON examples, and prepare persistent local PostgreSQL for development.
- [x] **PY-008 — Define the shelter domain and ingestion contracts.** Describe stones, profiles, shelters, cases, and incremental case events.
- [x] **PY-007 — Isolate integration tests.** Run PostgreSQL integration tests in disposable Testcontainers.
- [x] **PY-003 — Create stones.** Persist a stone with a UUID through the initial create endpoint.
- [x] **PY-002 — Add database support.** Add PostgreSQL settings, async SQLAlchemy sessions, Unit of Work, and Alembic migrations.
- [x] **PY-001 — Bootstrap the project.** Configure uv, FastAPI, Ruff, mypy, pytest, and Docker Compose.

## Current

No current tasks.

## Backlog

- [ ] Index existing local stones explicitly if they are needed for search experiments.
- [ ] Add typed PostgreSQL lookups for other exact operational questions.
- [ ] Combine lexical and vector evidence into a first hybrid retrieval path.
- [ ] Add LangChain tools and a bounded LangGraph in which an LLM chooses the relevant search path.
- [ ] Return an evidence-grounded answer through a minimal HTTP endpoint.
- [ ] Trace model and tool decisions with Langfuse and record the first working configuration.
- [ ] Build evaluation examples and measure retrieval and answer quality before changing the search design.
- [ ] Compare models, embeddings, chunking, fusion, and reranking through controlled experiments.
- [ ] Revisit source updates, indexing recovery, and broader application behavior only when selected as learning tasks.
