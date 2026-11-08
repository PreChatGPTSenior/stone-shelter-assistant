# PY-024: Compare representations, embeddings and query languages

## Why

Only the initial fourteen-section encyclopedia representation exists; no comparison harness or alternate model is connected.

## What Changes

- Compare chunking, profile/event granularity, embedding choices and languages one factor at a time.
- Use the authored JSON compatibility guide alongside the encyclopedia; the separate tarot idea is deferred.

## Capabilities

### New Capabilities
- `representation-and-language-experiments`: Compare representations, embeddings and query languages.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-017 and PY-019; use source corpus from PY-027/PY-028.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/27

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No arbitrary multi-model or large-corpus prerequisite for the pilot.
