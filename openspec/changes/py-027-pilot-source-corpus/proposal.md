# PY-027: Prepare the operational corpus and encyclopedia for the pilot

## Why

Ten valid stone JSON files, two shelters, the registration loader and an English encyclopedia exist. The encyclopedia function currently yields fourteen selected sections. The compatibility JSON source is now authored under ADR-0018; a separate tarot idea is deferred.

## What Changes

- Review and reuse the ten complete registration fixtures before adding only examples needed for the agreed retrieval paths.
- Inventory the operational corpus and both reference sources, with representative questions and exact source locations.
- Keep the existing encyclopedia and its fourteen-section preparation; inspect content and provenance rather than rewriting the corpus.

## Capabilities

### New Capabilities
- `pilot-source-corpus`: Prepare the operational corpus and encyclopedia for the pilot.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: First: source preparation. Dependencies: PY-010 (delivered); coordinate with PY-028.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

Local planning ID only; no GitHub issue has been created or numbered for this work.

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Large synthetic datasets, ANN benchmarks, negative-path fixtures, relevance labels and LLM judges belong to later evaluation work.
