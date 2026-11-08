# PY-024 design boundaries

## Current evidence

Reviewed on 2026-11-08. Only the initial fourteen-section encyclopedia representation exists; no comparison harness or alternate model is connected. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Compare whole sections with finer semantic/size-aware chunks while preserving qualifications and source IDs. Record grouping effects on stone candidates.

2. Include Russian questions over English content, paraphrases, negation, identifiers, unknown facts and distractors incrementally.

3. General/domain model choice requires a real model-card/license/runtime/input-limit review; do not assume a geology-tuned model improves fictional pet suitability.

4. Named/multiple vectors, ANN, quantization and corpus expansion are later sub-experiments; separate neighbor recall from semantic relevance.

## Dependencies and phase

After the connected pilot. PY-017 and PY-019; use source corpus from PY-027/PY-028. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/representation-and-language-experiments/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No arbitrary multi-model or large-corpus prerequisite for the pilot.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
