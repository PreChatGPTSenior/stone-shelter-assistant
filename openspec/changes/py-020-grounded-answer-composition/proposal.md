# PY-020: Compose evidence-grounded answers through LangChain

## Why

No context assembly, answer model call or citation response exists.

## What Changes

- Build a bounded evidence context and a reusable LangChain answer component.
- Support a fixed retrieval-to-answer exercise and reuse the same answer component inside PY-022; the fixed path alone is not the completed pilot.

## Capabilities

### New Capabilities
- `grounded-answer-composition`: Compose evidence-grounded answers through LangChain.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: answer composition. Dependencies: PY-018 and the PY-019 pilot slice.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/23

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Answer judges, full-context comparisons and broad quality matrices belong to PY-017/PY-024.
