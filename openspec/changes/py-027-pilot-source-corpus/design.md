# PY-027 design boundaries

## Current evidence

Reviewed on 2026-11-08. Ten valid stone JSON files, two shelters, the registration loader and an English encyclopedia exist. The encyclopedia function currently yields fourteen selected sections. The compatibility JSON source is now authored under ADR-0018; a separate tarot idea is deferred. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Use fixtures/stones/<stone.externalId>.json and the existing one-request-per-file loader. Seed shelters separately. A new loading run against populated local data is not authorized by this ticket.

2. Record a small human-readable corpus manifest under docs/search/ listing source paths, source families, fictional/geological boundaries and illustrative questions. This is not a judged evaluation dataset or an application JSONL intermediate.

3. Cover a missing profile, a populated profile, meaningful event history, current availability, type/size/shelter constraints and distinct preferences. Existing fixtures may already satisfy these cases; no arbitrary record-count expansion.

4. Use the authored compatibility JSON from PY-028 and update the source inventory. Do not add invented operational attributes to make those sources join.

## Dependencies and phase

First: source preparation. PY-010 (delivered); coordinate with PY-028. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/pilot-source-corpus/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Large synthetic datasets, ANN benchmarks, negative-path fixtures, relevance labels and LLM judges belong to later evaluation work.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
