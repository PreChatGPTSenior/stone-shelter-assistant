# PY-023 design boundaries

## Current evidence

Reviewed on 2026-11-08. Indexes are not implemented; no outbox/worker exists. ADR-0004 selects PostgreSQL-backed durable tasks rather than Kafka. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Initially use registration as an available write path. Profile updates/event append require PY-006 contracts first; do not invent mutation semantics in a worker ticket.

2. Track per-engine delivery, source revision and claim/retry state. Do not equate an individual row ORM version with a version of the whole stone graph.

3. Distinguish text changes needing embeddings from filter-only changes. A status/shelter update may affect all indexed operational documents for the stone.

4. Use bounded claims/retries, stable IDs and explicit stale-work handling; PostgreSQL is authoritative and indexes remain rebuildable without deleting operational data.

## Dependencies and phase

After the connected pilot. PY-018/PY-017; PY-006 only for mutation-specific scenarios. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/durable-indexing-and-freshness/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No Kafka, distributed transaction or production HA. Do not implement before the pilot.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
