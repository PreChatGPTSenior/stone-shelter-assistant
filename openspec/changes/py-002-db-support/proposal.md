# PY-002 Database support

> Historical PY-002 scope. Delivered and merged (fcc427d); see tasks.md for current evidence and deferred checks. PY-007 supersedes the original test-target workflow; ADR-0014 permits persistent local application data. The earlier CRUD sequence is not the current pilot plan.

## Why

The application starts and serves OpenAPI, but does not yet manage PostgreSQL connections or transactions. Establish this foundation before implementing simple Stone CRUD.

## What Changes

- Add validated database settings, async engine and session lifecycle.
- Introduce an explicit Unit of Work independent of business modules.
- Configure Alembic without introducing business tables.
- Verify connectivity, commit, rollback and session isolation against PostgreSQL.

## Capabilities

### New Capabilities
- `database-support`: validated configuration, bounded resource lifetimes, explicit transaction guarantees and a migration environment.

### Modified Capabilities
None. The existing HTTP bootstrap remains the baseline; runtime resources are attached through lifespan when implemented.

## Impact

Future changes to `settings.py`, application assembly, database infrastructure, the UoW contract, Alembic configuration and focused tests. Required Python dependencies and isolated PostgreSQL infrastructure already exist. This documentation setup does not implement those changes.

## Scope Boundary

No Stone or AdoptionListing models, business tables, CRUD routes, photos, embeddings, task queues, Redis integration, authentication or UI changes. No live data migration or destructive database operation is authorized by this proposal.

## Tracking

- Issue: [PY-002](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/2)
- Branch: `PY-002-db-support`
- Board: [Stone Shelter Python](https://github.com/users/PreChatGPTSenior/projects/1/views/1)
- Decisions: [ADR index](../../../docs/adr/README.md)
- Implementation: delivered for the agreed scope; issue #2 is closed. Current deferred verification is explicit in tasks.md.
