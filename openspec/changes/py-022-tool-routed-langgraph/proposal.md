# PY-022: Build a bounded LangGraph with real LLM tool selection

## Why

No LangGraph dependency, graph, tool contracts or routing implementation exists. The pilot must include actual LLM tool choice, not only a fixed graph.

## What Changes

- Pilot: interpret the request through a tool-capable LLM and execute typed application tools.
- Pilot: connect tool results, current-state checks and grounded answer in a bounded explicit LangGraph.
- Later: add clarification, follow-ups, rewriting, decomposition and controlled repeated retrieval.

## Capabilities

### New Capabilities
- `tool-routed-langgraph`: Build a bounded LangGraph with real LLM tool selection.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot slice, then post-pilot extension. Dependencies: PY-014, PY-018, PY-019 pilot and reusable answer composition from PY-020.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/25

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Free-form SQL, lifecycle mutations, unbounded loops and production agent recovery are excluded.
