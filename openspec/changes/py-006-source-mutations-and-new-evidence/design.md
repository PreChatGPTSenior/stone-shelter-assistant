# PY-006 design boundaries

## Current evidence

Reviewed on 2026-11-08. No update or event-append endpoint exists. The historical PUT/full-replacement issue is superseded; exact mutation DTOs are not agreed. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Explicitly settle identity, omitted versus null fields, collections, source ordering tokens and repeat delivery; these are contract decisions pending this task, not already supported APIs.

2. Current status and shelter remain source-owned snapshots. An event-append endpoint must not silently derive them by replay. If a request changes snapshot plus event, define the request and commit them atomically.

3. Keep events append-only and preserve case identity across returns/transfers. Start by explicit reindex for the experiment; automatic delivery belongs to PY-023.

## Dependencies and phase

After the connected pilot. PY-010 current contract; PY-017 for measuring new evidence; PY-023 for later automatic refresh. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/source-mutations-and-new-evidence/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No new mutation contract, DTO or endpoint is implemented by this plan. Not a pilot blocker.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
