# Typesense connection design

Use Pydantic settings with TYPESENSE_ prefix, required host/port/API key, SecretStr, a literal HTTP/HTTPS protocol and a positive timeout. Only explicit development startup loads .env. The factory receives settings; it does not read environment variables or perform HTTP requests itself.

The official typesense 2.1.1 AsyncClient uses its default httpx transport. FastAPI lifespan creates one client per app instance and exposes it through app.state.typesense_client. AsyncExitStack closes the client and disposes the database engine in reverse registration order, including startup failure after resource creation. Client creation does not require a reachable server and does not create an index.

The Typesense test container uses the same pinned server image, a random published port, an explicit test-only API key and no development volume. Test settings pass _env_file=None and every connection value explicitly. One container is shared per pytest session; async clients are function-scoped for the existing function-scoped event loop. Integration application fixtures supply these settings to lifespan instead of local configuration.

The owner-approved happy path requires no retry/fallback framework. /health is the fixture's readiness check; the SDK smoke test calls authenticated /debug. Collection isolation and actual indexing/search scenarios follow when those operations exist. JSONL corpus snapshots belong to later experiment tooling and are not an application intermediate layer.
