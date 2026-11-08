# PY-014: Retrieve lexical evidence and exact PostgreSQL candidates

## Why

The catalog repository only adds objects. No Typesense search or typed SQL search operation exists.

## What Changes

- Add lexical evidence retrieval with explicit query text, limits and filters.
- Add the typed PostgreSQL exact lookup and candidate/history hydration needed by tools and final checks.

## Capabilities

### New Capabilities
- `lexical-and-structured-retrieval`: Retrieve lexical evidence and exact PostgreSQL candidates.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: retrieval. Dependencies: PY-013.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/17

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Public catalog read endpoints remain PY-004; arbitrary SQL, exhaustive query evaluation and pagination products are not prerequisites.
