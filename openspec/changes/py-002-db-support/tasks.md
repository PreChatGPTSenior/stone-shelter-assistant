# PY-002 implementation checklist

Issue: [PY-002](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/2). Branch: `PY-002-db-support`.

This checklist records the manually implemented database infrastructure and remaining work. Checked items reflect reviewed files and the owner's reported verification results. Deferred work remains unchecked.

## 1. Configuration and resource lifecycle
- [x] 1.1 Define validated database settings and deliberate local environment loading; cover invalid configuration and secret handling.
- [x] 1.2 Configure the async engine and session factory without opening connections at import or factory-construction time.
- [x] 1.3 Connect engine lifetime to application lifespan and verify cleanup while retaining the factory-only OpenAPI test.

## 2. Explicit Unit of Work
- [x] 2.1 Define the transaction contract and SQLAlchemy implementation with explicit commit and rollback on uncommitted exit.
- [x] 2.2 Assemble UoW and persistence participants around one session per execution; release sessions reliably. Delivered infrastructure in PY-002; real repository/service composition now exists in PY-010. See bootstrap/dependencies.py and application/register_stone.py.
- [x] 2.3 Verify authenticated PostgreSQL connectivity, commit, normal-exit rollback, exception rollback and commit failure reporting.
- [ ] 2.4 Verify two independent UoW executions. **Still unverified:** the dedicated two-UoW isolation scenario. PY-010 now verifies atomic rollback of a real multi-table graph on constraint failure; that does not establish isolation between two independent UoWs or constitute a two-repository test.

## 3. Migration environment
- [x] 3.1 Define the shared declarative base and configure Alembic with settings-backed connectivity and metadata.
- [x] 3.2 Verify revision inspection on the isolated database without creating business tables or enabling automatic startup migrations.

## 4. Review and handoff
- [x] 4.1 Document the implemented connection, migration and focused test commands without credentials. See [local setup instructions](../../../docs/setup.md).
- [x] 4.2 Run Ruff lint/format checks, mypy and the relevant focused tests; record real outcomes. The owner reported successful Ruff lint and format checks, mypy, and the full pytest suite. The owner also verified Alembic upgrade, downgrade, and re-upgrade against local PostgreSQL. Exact test counts were not recorded.
- [x] 4.3 Review the agreed infrastructure scope and update delivery status. PY-002 was merged and issue #2 closed; the independently deferred scenario above remains unverified.

## Current handoff (2026-11-05)

- PY-002 is delivered for its agreed infrastructure scope; commit f0f5dcb, merge fcc427d. Issue #2 is closed.
- Explicit commit and both rollback exits have PostgreSQL integration coverage. Commit failure propagation/cleanup has mock-based coverage.
- PY-007 moved database-backed automated checks to Testcontainers. PY-010 supplies real repository composition and graph rollback coverage. Application persistence is allowed by ADR-0014; tests never target it.
- A dedicated test of two independent UoW executions remains deferred and unverified. Do not mark it complete based on an independent read session.
- The change directory is retained as historical evidence; this documentation update does not archive it or claim a fresh application test run.
