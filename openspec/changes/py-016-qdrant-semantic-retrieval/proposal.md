# PY-016: Connect Qdrant, index vectors and retrieve semantic evidence

## Why

Qdrant is selected and the local Compose service is configured. Python dependencies, client lifecycle, collections, indexing, retrieval and isolated test support are pending.

## What Changes

- Add local Qdrant settings/client/lifecycle and disposable test infrastructure.
- Index the same prepared evidence IDs and external vectors; expose filtered semantic retrieval.

## Capabilities

### New Capabilities
- `qdrant-semantic-retrieval`: Connect Qdrant, index vectors and retrieve semantic evidence.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: vector retrieval. Dependencies: PY-011 and PY-015.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/19

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

ANN tuning, quantization, multiple vectors, failure injection and recovery are later work.
