# PY-030: Expose and verify the connected search assistant pilot

## Why

Only the registration endpoint exists. No question/answer entrypoint or complete search-assistant scenario is implemented.

## What Changes

- Add one minimal HTTP question/answer entrypoint with typed responses and source references.
- Exercise the complete graph and retrieval across PostgreSQL, Typesense and Qdrant.
- Provide an explicit separately invoked real-model demonstration before declaring the pilot complete.

## Capabilities

### New Capabilities
- `connected-search-pilot`: Expose and verify the connected search assistant pilot.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: final connected result. Dependencies: PY-020 and PY-022 pilot slices; PY-019 tracing; prepared source corpus.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

Local planning ID only; no GitHub issue has been created or numbered for this work.

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No full UI, SSE/token streaming, chat persistence, authentication, production deployment or exhaustive regression dataset.
