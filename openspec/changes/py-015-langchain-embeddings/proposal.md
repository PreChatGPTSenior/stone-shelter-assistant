# PY-015: Generate document and query embeddings through LangChain

## Why

Only langchain-text-splitters is installed. No embedding provider, model selection or generation code exists.

## What Changes

- Select one embedding model/integration and make its input/output contract explicit.
- Generate document and query vectors from the agreed texts and retain configuration identity.

## Capabilities

### New Capabilities
- `langchain-embeddings`: Generate document and query embeddings through LangChain.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: Pilot: embeddings. Dependencies: PY-011 and prepared corpus; independent of Typesense availability.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/18

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

Multiple embedding models, representation comparisons, migration/version machinery and named vectors belong to PY-024.
