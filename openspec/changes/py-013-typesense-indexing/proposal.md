# PY-013: Create Typesense collections and index prepared evidence

## Why

Typesense connection exists locally; no collection schema, index command or document import is implemented.

## What Changes

- Define concrete lexical collection schemas for operational evidence and reference knowledge.
- Populate them directly from prepared document objects using an explicit indexing command.
- Support repeatable upserts by shared evidence ID.

## Capabilities

### New Capabilities
- `typesense-indexing`: Create Typesense collections and index prepared evidence.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: indexing. Dependencies: PY-011 and PY-012; source corpus PY-027/PY-028.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/16

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Automatic refresh, workers, retries, stale-job ordering and generic schema migration remain PY-023.
