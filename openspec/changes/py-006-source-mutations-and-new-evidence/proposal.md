# PY-006: Define source updates and append history for later retrieval experiments

## Why

No update or event-append endpoint exists. The historical PUT/full-replacement issue is superseded; exact mutation DTOs are not agreed.

## What Changes

- Agree source-owned partial update and separate event-append contracts before implementation.
- Use changed profiles/history to observe new evidence in retrieval.

## Capabilities

### New Capabilities
- `source-mutations-and-new-evidence`: Define source updates and append history for later retrieval experiments.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-010 current contract; PY-017 for measuring new evidence; PY-023 for later automatic refresh.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/6

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No new mutation contract, DTO or endpoint is implemented by this plan. Not a pilot blocker.
