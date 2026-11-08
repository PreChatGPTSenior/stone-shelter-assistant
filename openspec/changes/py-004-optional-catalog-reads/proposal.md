# PY-004: Provide optional catalog inspection endpoints

## Why

GET collection/item routes are absent. Tools need typed SQL operations but do not require public catalog endpoints.

## What Changes

- Retain the existing ticket for an optional plain list/read inspection surface, separately from search tools.

## Capabilities

### New Capabilities
- `optional-catalog-reads`: Provide optional catalog inspection endpoints.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Deferred product convenience; not a pilot prerequisite. Dependencies: Existing registration; reuse appropriate typed queries from PY-014 if available.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/4

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No search pilot dependency, physical deletion, UI or full CRUD expansion.
