# PY-018 design boundaries

## Current evidence

Reviewed on 2026-11-08. No retrieval orchestration or fusion implementation exists. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Start with reciprocal-rank fusion: sum 1/(k + rank) for each branch containing an evidence ID. Record k, one-based ranks and per-branch limits; do not add incomparable raw backend scores.

2. Deduplicate by evidence ID before grouping by stone_external_id. Start with the strongest fused evidence score per stone and retain supporting passages; do not reward long histories merely for more documents. This simple choice is measurable later.

3. Keep reference passages in their own ranked scope; they are supporting knowledge, not candidate pets.

4. Recheck current existence, type/size constraints, source-owned status and current shelter through PostgreSQL before recommending; a generic case lookup can still display unavailable cases.

## Dependencies and phase

Pilot: hybrid retrieval. PY-014 and PY-016; PY-017 is not a dependency. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/hybrid-retrieval/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Fusion tuning, recovery branches, reranking and comprehensive stale-index experiments follow the baseline.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
