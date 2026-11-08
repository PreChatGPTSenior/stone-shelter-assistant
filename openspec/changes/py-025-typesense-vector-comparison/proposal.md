# PY-025: Compare Typesense vectors and built-in hybrid with the initial pipeline

## Why

Typesense is selected for lexical retrieval only. Its vector and built-in hybrid behavior is a separate later experiment.

## What Changes

- Compare Typesense vector-only and built-in hybrid to Qdrant vectors plus Python RRF using controlled shared inputs.

## Capabilities

### New Capabilities
- `typesense-vector-comparison`: Compare Typesense vectors and built-in hybrid with the initial pipeline.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-017 and PY-018; same embedding assets from PY-015.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/28

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No replacement of Qdrant in the initial architecture; no simultaneous addition of Solr or pgvector.
