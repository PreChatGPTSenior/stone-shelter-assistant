# PY-026 design boundaries

## Current evidence

Reviewed on 2026-11-08. No Spring AI implementation is part of this Python feature. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Choose Java repository and implementation boundaries when the owner starts this exercise. Do not add a Java service to the Python application implicitly.

2. Reuse corpus snapshots, queries/judgments, embeddings where practical, filters, prompts/models and budgets; record unavoidable differences.

3. A Spring AI VectorStore adapter need not expose full lexical/hybrid APIs; compare observable behavior rather than force identical internal framework structures.

## Dependencies and phase

After the measured Python baseline. PY-017; PY-020/PY-022 behavior and shared experiment assets. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/spring-ai-comparison/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No Java implementation or dependency changes in this documentation work.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
