# Repository organization

Keep the structure small and follow the responsibilities below when adding or moving code.

Application paths below are relative to `src/stone_shelter_assistant`.

1. **Organize by feature.** Use `stones`, `search`, and `assistant`, with shared technical foundations in `core`. Create a package when implemented functionality gives it a concrete responsibility. Avoid speculative scaffolding and empty placeholder modules.

2. **Keep feature code together.** Stone registration routers, API contracts, services, repositories, enums, and ORM models belong in `stones`. Agent-driven matching and question-answering flows belong in `assistant`.

3. **Keep shared foundations in `core`.** Store application settings, API and ORM bases, PostgreSQL connection factories, and Unit of Work here. Put search-specific components in `search`. Extract shared components when actual callers need them.

4. **Assemble the application at the package root.** `app.py` creates FastAPI and manages shared resource lifecycles. `dependencies.py` wires request-scoped dependencies. Uvicorn loads the application through the `app.py` factory.

5. **Respect the search subpackages.** `search/infrastructure` owns client factories, collection schemas, and collection setup. `search/stones` prepares and indexes stone, profile, and case-event documents. `search/knowledge` processes and indexes reference sources. Shared search document models, content helpers, and enums live directly in `search`.

6. **Separate document preparation from external calls.** Builders transform supplied data into validated search documents. Indexers accept prepared documents and write them to their search engine, computing embeddings where required. Services coordinate data retrieval, document preparation, and indexing. Build a shared projection once when sending the same document to both engines.

7. **Use descriptive names and cohesive files.** Prefer names such as `api_contracts.py`, `repository_protocols.py`, and `document_content.py`. Keep related small classes together. Split a file when its responsibilities become distinct or it becomes difficult to navigate.

8. **Keep simulated input data in `fixtures`.** Stone examples belong in `fixtures/stones`, and reference knowledge in `fixtures/knowledge`. Test-only invalid scenarios belong in `tests/fixtures`. Treat knowledge files as authored examples of supplied sources in this fictional learning project.

9. **Complete moves through their callers.** Update imports, fixture paths, tests, and affected documentation when renaming or moving files. Verify the affected application entry points and scenarios.

10. **Load ORM relationships explicitly.** Declare relationships with `lazy="raise"` and load the relationships needed by each query explicitly, for example with `selectinload`.
