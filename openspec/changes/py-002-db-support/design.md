# PY-002 Database support design

> Historical PY-002 scope. Delivered and merged (fcc427d); see tasks.md for current evidence and deferred checks. PY-007 supersedes the original test-target workflow; ADR-0014 permits persistent local application data. The earlier CRUD sequence is not the current pilot plan.

## Context

The Python project already has an application factory, uv-managed dependencies and a PostgreSQL 18.6 container reachable from the host at port 55432 by default. The actual connection target is configuration-driven. This change adds infrastructure only; Stone CRUD follows in PY-003 through PY-006.

## Decisions

- Follow [ADR-0001](../../../docs/adr/0001-modular-monolith.md): keep one Python project and compose dependencies at the application boundary.
- Follow [ADR-0003](../../../docs/adr/0003-explicit-unit-of-work.md): share one session per use-case execution, require explicit commit and keep UoW unaware of business repositories.
- Follow [ADR-0005](../../../docs/adr/0005-incremental-manual-development.md): human-written implementation, PostgreSQL-only runtime dependency for this stage and test-driven API verification without UI work.

## Responsibility map

| Location | Future responsibility |
| --- | --- |
| `src/stone_shelter/settings.py` | Pydantic settings and deliberate environment loading; Compose reading `.env` does not configure Python automatically |
| `src/stone_shelter/application/transactions.py` | Framework-independent transaction contract |
| `src/stone_shelter/infrastructure/database/engine.py` | Async SQLAlchemy engine configuration using `postgresql+asyncpg` |
| `src/stone_shelter/infrastructure/database/session.py` | Session factory; no global mutable session |
| `src/stone_shelter/infrastructure/database/unit_of_work.py` | Transaction and session lifetime, explicit commit, rollback and cleanup |
| `src/stone_shelter/infrastructure/database/base.py` | Shared declarative base and metadata |
| `src/stone_shelter/bootstrap/` | Composition and lifespan management; bind transaction participants to the same session |
| `alembic.ini` and `migrations/env.py` | Migration configuration and access to the shared metadata |
| `tests/integration/` | Focused PostgreSQL connectivity and transaction tests with isolated disposable data |

## Transaction boundary

The outer use case owns the commit decision. Its UoW and persistence participants are assembled around the same session. Participants execute sequentially within that session. An independent concurrent operation receives a different session. SQLAlchemy `flush` may issue SQL without committing.

Create and dispose the engine through the runtime lifecycle; defer connection acquisition until database use. The current factory-only OpenAPI test must remain usable without starting PostgreSQL. Tests that enter the new lifespan must manage it explicitly.

Construct connection URLs from separate fields using SQLAlchemy URL utilities so special characters in passwords are handled correctly. Avoid embedding credentials in `alembic.ini`, committed files or diagnostics.

## Verification and constraints

Use PostgreSQL, not SQLite, for transaction guarantees. Use a dedicated disposable test target or isolated test schema and clean up test fixtures. Do not change the Java project's containers or volumes. No model calls, buckets, business imports or production migrations are needed.

Alembic is prepared here, but business revisions start in PY-003. Document runnable commands as implementation lands. No automatic migrations on application startup are planned.

## Deferred decisions

Exact pool sizing, concrete class signatures and test-fixture lifetime will be worked through with the owner during implementation. Do not preselect a repository hierarchy or add Redis, Testcontainers, authentication or a scheduler under this ticket without a scope discussion.
