# Architecture Decisions

This compact record captures current choices and their reasons. The fictional premise and learning goal take precedence over production completeness.

- **Learning scope:** Build a working happy-path pilot first, then evaluate and improve it. The exercise teaches Python, hybrid search, RAG, agent routing, and evaluation.
- **Project stack:** Use uv, FastAPI, Pydantic, SQLAlchemy with asyncpg, Alembic, Ruff, mypy, and pytest-asyncio. Add other libraries only when their learning task needs them.
- **Code ownership:** The owner writes application code while learning; assistance focuses on explanation, review, and explicitly delegated edits.
- **Architecture:** Keep a small modular FastAPI application with explicit services, repositories, and a Unit of Work for PostgreSQL transactions. Do not add a separate domain dataclass layer merely to copy validated DTO fields into ORM entities.
- **Operational model:** A stone has intrinsic properties; one globally identified lifetime ShelterCase owns current adoption status and shelter, and CaseEvents record history. The upstream source supplies current status; do not reconstruct it from event order.
- **Registration:** Accept one stone with a required case and admission event per request; profile is optional. PostgreSQL commits the graph before the pilot indexes it. This is not an atomic transaction across search engines.
- **Data ownership:** PostgreSQL is authoritative for operational facts. Search indexes are rebuildable projections, and recommendations must recheck current eligibility in PostgreSQL.
- **Test isolation:** Automated database and search integration tests use disposable Testcontainers and controlled embeddings. The local application uses persistent PostgreSQL; never reset its data as a side effect of testing.
- **Reference sources:** Keep the Markdown encyclopedia and fictional JSON type-compatibility guide as authored files. The compatibility guide has ten type portraits, 55 symmetric pair rules, and reading guidance; pair-specific advice must preserve both types and its source identity. The separate tarot idea is deferred.
- **Knowledge loading:** Explicit local endpoints may reindex each known reference file without changing its authored content. Stable evidence IDs let the same file be indexed again without creating duplicates.
- **Search engines:** Use Typesense for lexical retrieval and Qdrant for vectors computed explicitly with an embedding model. Keep reference evidence distinct from operational stone filters. Use typed PostgreSQL queries for purely exact requests.
- **Models:** Start with local Ollama embeddings and allow selected OpenRouter models for generation experiments. Measure token use and keep explicit experiment budgets; do not call a paid model from ordinary tests.
- **Agent path:** Use LangChain tools and a bounded LangGraph so an LLM can select appropriate retrieval; the answer must cite evidence. Test conversations remain short, at most five turns.
- **Observability and evaluation:** Start with Langfuse tracing and a recorded baseline. Evaluate retrieval and free-form answer quality after the first working pilot; then compare strategies, models, prompts, and costs.
- **Deferred operations:** Queues, outbox delivery, retries, automatic cross-index recovery, full CRUD/UI, and production deployment are not prerequisites for the pilot. Keep failures visible rather than claiming distributed atomicity.
- **Documentation:** Keep one manifesto, one task log, this decision record, and setup instructions. OpenSpec is not part of this project's current workflow.
