# PY-019: Connect generation providers, Langfuse and experiment accounting

## Why

Ollama, OpenRouter and Langfuse Cloud Hobby are accepted choices but no integrations are installed or wired.

## What Changes

- Pilot: connect one selected tool-capable generation model through LangChain and minimum useful Langfuse tracing.
- Later: add the other provider, experiment token/cost budgets and complete accounting for generation, embeddings and judges.

## Capabilities

### New Capabilities
- `providers-tracing-and-budgets`: Connect generation providers, Langfuse and experiment accounting.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot slice, then post-pilot extension. Dependencies: PY-015 for embedding observations; retrieval operations for the connected trace.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/22

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Full accounting does not block the first result. No hosted account creation, credential upload or paid inference is performed by this planning change.
