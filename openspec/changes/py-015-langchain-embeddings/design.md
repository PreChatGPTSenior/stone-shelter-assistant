# PY-015 design boundaries

## Current evidence

Reviewed on 2026-11-08. Only langchain-text-splitters is installed. No embedding provider, model selection or generation code exists. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Record model/provider/revision, dimensions, metric, document/query preprocessing and input limits. Verify the actual chosen model before adding its integration.

2. Use title plus evidence text as the initial document input, consistent with the existing encyclopedia content hash. Do not embed volatile availability metadata as evidence text.

3. Preserve the model's required document/query prefixes if any. Inspect complete encyclopedia chapters and authored new sources against the selected limit; split explicitly when necessary, never silently truncate.

4. Bound batch size and invoke real embeddings explicitly. Use controlled embedding results for ordinary orchestration tests; do not make make check spend money or require local models.

## Dependencies and phase

Pilot: embeddings. PY-011 and prepared corpus; independent of Typesense availability. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/langchain-embeddings/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Multiple embedding models, representation comparisons, migration/version machinery and named vectors belong to PY-024.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
