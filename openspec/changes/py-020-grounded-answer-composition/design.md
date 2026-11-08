# PY-020 design boundaries

## Current evidence

Reviewed on 2026-11-08. No context assembly, answer model call or citation response exists. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Keep individual observations, history, geological/reference guidance, fictional compatibility guidance distinguishable by provenance.

2. Pass current PostgreSQL candidate identities/state separately from historical and reference evidence. Cite actual document/source IDs and sections rather than invented URLs.

3. Bound context using the selected model budget and preserve important qualifications; do not silently cut source conditions.

4. No missing profile or unlisted compatibility implies suitability. Answer only from supplied evidence; full hallucination evaluation belongs after the pilot.

## Dependencies and phase

Pilot: answer composition. PY-018 and the PY-019 pilot slice. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/grounded-answer-composition/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Answer judges, full-context comparisons and broad quality matrices belong to PY-017/PY-024.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
