# PY-013 design boundaries

## Current evidence

Reviewed on 2026-11-08. Typesense connection exists locally; no collection schema, index command or document import is implemented. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. PY-011 owns source-to-document preparation. This task owns Typesense schema/serialization/import, not a second projection implementation.

2. Use separate operational and reference collections, or equally explicit isolated query scopes; finalize collection names in implementation documentation. Enable filtering only on the fields actually needed.

3. Serialize UUIDs/enums/dates deliberately. Document ID is the shared evidence UUID string, not a newly generated Typesense-only identity.

4. Read PostgreSQL through bounded, explicit graph-loading queries and reference Markdown and compatibility JSON through their respective preparation functions. Do not insert a JSONL storage/export layer into the application.

5. An upsert of the same corpus must not duplicate documents. Full replacement/deletion of existing collections or business data is not implicit; use disposable test indexes for rebuild experiments.

## Dependencies and phase

Pilot: indexing. PY-011 and PY-012; source corpus PY-027/PY-028. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/typesense-indexing/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Automatic refresh, workers, retries, stale-job ordering and generic schema migration remain PY-023.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
