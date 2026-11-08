# PY-016 design boundaries

## Current evidence

Reviewed on 2026-11-08. Qdrant is configured in local Compose with a persistent volume and loopback host port. Python dependencies, client lifecycle, collections and isolated tests are absent. No model calls were run for this documentation audit.

## Responsibilities and decisions

1. Choose a supported async client and pin a compatible server when implementing, after inspecting actual versions. Define vector size and metric from PY-015, not a placeholder example.

2. Reuse evidence UUIDs as point identities and payload provenance across engines. Maintain explicit operational/reference scopes and useful payload indexes.

3. Copy current-state operational filters; reference knowledge remains independent of case status and shelter.

4. Test the real database adapter with small controlled vectors in Testcontainers; live model generation remains a separate explicit exercise.

## Dependencies and phase

Pilot: vector retrieval. PY-011 and PY-015. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/qdrant-semantic-retrieval/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

ANN tuning, quantization, multiple vectors, failure injection and recovery are later work.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
