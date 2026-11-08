# PY-018: Fuse lexical and vector evidence and verify current candidates

## Why

No retrieval orchestration or fusion implementation exists.

## What Changes

- Run lexical and semantic branches with common hard filters and bounded limits.
- Fuse document ranks, group evidence by stone and verify final candidates against PostgreSQL.

## Capabilities

### New Capabilities
- `hybrid-retrieval`: Fuse lexical and vector evidence and verify current candidates.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: hybrid retrieval. Dependencies: PY-014 and PY-016; PY-017 is not a dependency.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/21

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Fusion tuning, recovery branches, reranking and comprehensive stale-index experiments follow the baseline.
