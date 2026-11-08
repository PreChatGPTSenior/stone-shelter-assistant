# PY-025 design boundaries

## Current evidence

Reviewed on 2026-11-08. Typesense is selected for lexical retrieval only. Its vector and built-in hybrid behavior is a separate later experiment. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Reuse identical external vectors, IDs, corpus, filter semantics and metric wherever supported. Do not regenerate embeddings and attribute the result to the engine.

2. Report exact/ANN recall separately from relevance. Built-in fusion may differ from Python RRF; document those algorithm differences.

3. Add Solr/pgvector only for a specific separately selected research question, not automatically because a PostgreSQL extension image exists.

## Dependencies and phase

After the connected pilot. PY-017 and PY-018; same embedding assets from PY-015. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/typesense-vector-comparison/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No replacement of Qdrant in the initial architecture; no simultaneous addition of Solr or pgvector.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
