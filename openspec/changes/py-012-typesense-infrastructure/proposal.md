# PY-012: Typesense infrastructure and asynchronous connection

## Why

The prepared encyclopedia documents need a real lexical backend for the first pilot. Add only local infrastructure, validated connection settings, an async client and isolated test wiring before collection/indexing work.

## What Changes

- Add the pinned Typesense 30.2 Compose service with local-only host publication and a separate persistent index volume.
- Add TypesenseSettings and the official typesense AsyncClient factory, using the installed httpx transport and no automatic retries.
- Own the client in FastAPI lifespan and close its pool alongside PostgreSQL resources.
- Supply explicit Testcontainers-only settings and function-scoped async clients to integration tests.

## Capabilities

### New Capabilities
- `typesense-connection`: lifecycle-managed, authenticated connection to the selected lexical backend.

### Modified Capabilities
None. Registration contracts and business persistence stay unchanged.

## Impact

settings.py, infrastructure/typesense.py, bootstrap/app.py, dependency lock, environment template, Compose, setup docs and existing lifecycle/integration tests. No collection, indexing, search route, snapshot export or model call is introduced.

## Tracking

Issue: https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/15. This implementation is currently local in the existing PY-011 worktree; it does not claim a branch switch, commit or completed retrieval.
