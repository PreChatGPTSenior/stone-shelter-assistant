# PY-004 design boundaries

## Current evidence

Reviewed on 2026-11-08. GET collection/item routes are absent. Tools need typed SQL operations but do not require public catalog endpoints. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. When selected, agree current response fields against docs/domain/model.md rather than revive the old flat Stone contract.

2. Use bounded/deliberate list behavior and deterministic ordering; exact HTTP list contract remains to be reviewed for the current model.

## Dependencies and phase

Deferred product convenience; not a pilot prerequisite. Existing registration; reuse appropriate typed queries from PY-014 if available. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/optional-catalog-reads/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No search pilot dependency, physical deletion, UI or full CRUD expansion.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
