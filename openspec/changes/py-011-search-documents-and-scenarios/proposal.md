# PY-011: Prepare shared pilot search evidence

## Why

The source corpus needs concrete shared evidence units before either index can be populated. Pydantic models and fourteen encyclopedia sections are published in master; operational projection and new reference families remain pending.

## What Changes

- Reuse the existing evidence models and encyclopedia preparation.
- Read actual stored stones, optional profiles and case events into traceable operational documents.
- Add deliberate reference representations and preparation for the authored JSON type-compatibility source after PY-028.
- Return prepared document objects directly to later index adapters; no application JSONL export/storage layer.

## Capabilities

### New Capabilities
- `search-evidence-preparation`: shared source-faithful operational and reference documents.

### Modified Capabilities
None. Registration, ORM entities and source-owned status remain unchanged.

## Impact

Planned search preparation/read operations, focused scenarios and documentation. This planning pass edits no code. Typesense collection integration belongs to PY-013; vectors and Qdrant belong to PY-015/PY-016.

## Tracking

Issue: https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14.
Dependencies: delivered PY-010 and source preparation PY-027/PY-028 (new local planning IDs, not remote issue numbers).
See [delivery plan](../../../docs/search/pilot-delivery-plan.md), docs/project-manifesto.md and ADR-0017.

## Scope Boundary

No full relevance dataset, final universal schemas, generic source framework, automatic synchronization or provider calls. Corpus snapshots are a later PY-017 experiment-tool concern.
