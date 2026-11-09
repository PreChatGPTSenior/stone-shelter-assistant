# Task Log

Check a task only when its described behavior has been implemented and observed. This is a learning checklist, not a release plan.

## Done

- [x] Bootstrap the Python project with uv, FastAPI, Ruff, mypy, pytest, and Docker Compose.
- [x] Add PostgreSQL settings, async SQLAlchemy sessions, Unit of Work, and Alembic migrations.
- [x] Run database integration tests against disposable Testcontainers PostgreSQL.
- [x] Register one stone with its shelter case, optional profile, and supplied events through HTTP.
- [x] Prepare ten authored stone-registration JSON examples and a persistent local PostgreSQL development database.
- [x] Add an English stone encyclopedia and split it into fourteen search documents.
- [x] Author a fictional JSON compatibility guide covering ten types and all 55 unordered pairs.
- [x] Connect a Typesense client and verify it against a disposable Typesense container.
- [x] Build an initial stone search document and index one registration through HTTP into Typesense and Qdrant using controlled test embeddings.

## Next

- [ ] Parse the compatibility JSON into searchable pair, type-portrait, and guide-rule evidence.
- [ ] Create separate reference collections in Typesense and Qdrant and index encyclopedia and compatibility evidence.
- [ ] Add a small Knowledge API with explicit encyclopedia and compatibility reindex endpoints.
- [ ] Inspect real reference documents in both indexes through focused Testcontainers scenarios.
- [ ] Prepare and index optional stone-profile and case-event evidence.
- [ ] Index existing local stones explicitly if they are needed for search experiments.
- [ ] Implement inspectable Typesense lexical retrieval and Qdrant semantic retrieval.
- [ ] Implement typed PostgreSQL lookup for exact operational questions and verify current state before recommendations.
- [ ] Combine lexical and vector evidence into a first hybrid retrieval path.
- [ ] Add LangChain tools and a bounded LangGraph in which an LLM chooses the relevant search path.
- [ ] Return an evidence-grounded answer through a minimal HTTP endpoint.
- [ ] Trace model and tool decisions with Langfuse and record the first working configuration.
- [ ] Build evaluation examples and measure retrieval and answer quality before changing the search design.
- [ ] Compare models, embeddings, chunking, fusion, and reranking through controlled experiments.
- [ ] Revisit source updates, indexing recovery, and broader application behavior only when selected as learning tasks.
