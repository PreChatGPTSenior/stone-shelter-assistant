# PY-014 design boundaries

## Current evidence

Reviewed on 2026-11-08. The catalog repository only adds objects. No Typesense search or typed SQL search operation exists. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Keep search evidence results separate from grouped candidate results. Preserve document ID, source family, parent IDs, text, rank and backend score meaning.

2. Use typed parameterized SQLAlchemy operations for type/size/status/shelter/identity lookup; no unrestricted LLM SQL. Full public CRUD is unnecessary.

3. Allow independent reference queries by source family and relevant rock types; do not apply individual availability/shelter filters to general knowledge.

4. No implicit AVAILABLE filter for generic case lookup. An adoption recommendation explicitly requires AVAILABLE; exact historical case lookup may return other states.

## Dependencies and phase

Pilot: retrieval. PY-013. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/lexical-and-structured-retrieval/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Public catalog read endpoints remain PY-004; arbitrary SQL, exhaustive query evaluation and pagination products are not prerequisites.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
