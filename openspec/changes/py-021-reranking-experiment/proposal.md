# PY-021: Measure a separate reranking stage

## Why

No reranker is selected or installed.

## What Changes

- Add an optional bounded second ranking stage and compare against the same frozen hybrid candidates.

## Capabilities

### New Capabilities
- `reranking-experiment`: Measure a separate reranking stage.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-017, PY-018 and PY-019 accounting.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/24

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No reranker requirement for the first hybrid or agentic answer.
