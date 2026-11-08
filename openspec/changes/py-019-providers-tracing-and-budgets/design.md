# PY-019 design boundaries

## Current evidence

Reviewed on 2026-11-08. Ollama, OpenRouter and Langfuse Cloud Hobby are accepted choices but no integrations are installed or wired. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Use langchain-ollama for Ollama; choose the supported OpenRouter integration when implementation starts. Confirm tool calling with the selected serving model. An API key's existence does not identify the model or authorize a spending limit.

2. Trace query interpretation, chosen tool and validated arguments, retrieval evidence/ranks/filters, current-state exclusions and final answer; capture observable choices, not hidden chain-of-thought.

3. Record provider/model, per-call IDs, durations and usage provenance; missing tokens/cost remain unknown. Keep credentials/headers out of prompts, traces and result artifacts.

4. Pilot uses explicit call/output/context bounds. Later budgets cover run/case limits, input/output tokens, currency estimates, provider-reported charges, cached/reasoning tokens without double counting and a separate judge allowance.

5. Estimate and reserve capacity before the next paid call, reconcile actual usage after it and stop further scheduling at the limit. Provider-reported totals can arrive later; do not promise a perfect charge cap from estimates. Unknown price/usage is never zero.

6. Use local experiment artifacts independently of Langfuse retention. Recheck current Hobby terms at account setup; do not embed a historical quota as a permanent guarantee.

## Dependencies and phase

Pilot slice, then post-pilot extension. PY-015 for embedding observations; retrieval operations for the connected trace. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/providers-tracing-and-budgets/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Full accounting does not block the first result. No hosted account creation, credential upload or paid inference is performed by this planning change.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
