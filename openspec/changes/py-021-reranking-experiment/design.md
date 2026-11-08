# PY-021 design boundaries

## Current evidence

Reviewed on 2026-11-08. No reranker is selected or installed. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Select a concrete cross-encoder or deliberately chosen alternative when the experiment starts. Record input truncation policy, model revision, cost/local resources and score interpretation.

2. Hold retrieval candidates and corpus fixed while enabling reranking; retain original ranks and source references. Distinguish cross-encoder relevance from vector similarity rescoring.

## Dependencies and phase

After the connected pilot. PY-017, PY-018 and PY-019 accounting. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/reranking-experiment/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No reranker requirement for the first hybrid or agentic answer.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
