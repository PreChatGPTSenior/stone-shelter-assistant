# PY-017 design boundaries

## Current evidence

Reviewed on 2026-11-08. No evaluation runner or chosen evaluation framework exists. Source examples and existing tests are not relevance judgments. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Distinguish evidence-level recall/precision/ranking from candidate-level suitability and hard-constraint violations. A dataset must record the applicable corpus and current source snapshot.

2. Store questions, constraints, expected evidence/candidates and unacceptable claims with human review. Start small; held-out/no-result/unknown/multilingual cases expand later.

3. Compare SQL, lexical, vector and hybrid baselines; compare fixed and tool-routed answering. Direct-model and full-context baselines are controlled experiments, not mandatory application routes.

4. Record configuration, corpus/hash identity, source IDs, prompt/model/provider, branch limits/fusion, predictions, latency, usage/cost and trace references. Snapshots/JSONL may exist inside separate experiment tooling, never as required application storage.

5. Calibrate a later LLM judge against human-reviewed cases and budget it separately. Framework choice remains open; the earlier spoken “EVIL” refers to evaluation, not an installed or selected package.

## Dependencies and phase

After the connected pilot. PY-030; retrieval and trace outputs; PY-019 budgets for live runs. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/retrieval-and-answer-evaluation/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No framework installation or live evaluation in this docs-only change. Comprehensive datasets and judges do not block PY-030.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
