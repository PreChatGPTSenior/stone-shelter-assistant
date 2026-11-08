# PY-012 connection checklist

- [x] Add pinned local Compose infrastructure and separate persistent index volume without changing existing service targets.
- [x] Add validated TypesenseSettings and environment-template/local host configuration.
- [x] Add an async SDK factory with explicit caller-owned lifecycle and no automatic retries.
- [x] Register client creation/cleanup in FastAPI lifespan and adapt the existing lifecycle test.
- [x] Add Testcontainers-only settings and function-scoped async clients; adapt app fixtures without local .env fallback.
- [x] Verify an authenticated SDK request to the disposable container and run the existing checks. make check passed: Ruff, formatting, strict mypy (82 source files), and 43 tests. The SDK emits an AnalyticsV1 deprecation warning during client construction; no analytics API is used or warning suppressed.
- [x] Document the connection/ownership boundaries and defer JSONL export, collection/indexing/search and model calls.

This checklist records connection work, not completion of search or indexing. No commit or merge is authorized by it.
