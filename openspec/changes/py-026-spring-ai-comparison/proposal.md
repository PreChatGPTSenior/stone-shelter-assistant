# PY-026: Reproduce measured Python behavior with Spring AI

## Why

No Spring AI implementation is part of this Python feature.

## What Changes

- Reproduce comparable retrieval/answer/tool behavior in a separately selected Java workspace and evaluate with shared assets.

## Capabilities

### New Capabilities
- `spring-ai-comparison`: Reproduce measured Python behavior with Spring AI.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the measured Python baseline. Dependencies: PY-017; PY-020/PY-022 behavior and shared experiment assets.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/29

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No Java implementation or dependency changes in this documentation work.
