# PY-030 design boundaries

## Current evidence

Reviewed on 2026-11-08. Only the registration endpoint exists. No question/answer entrypoint or complete search-assistant scenario is implemented. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Finalize the concrete route and DTO names when implementing; this plan does not invent a published HTTP contract. No UI, sessions, Redis or token streaming is required.

2. Return an answer, relevant candidate identities, evidence/source references and a trace ID when configured. Expose no provider credentials or hidden reasoning.

3. Use real Testcontainers backends with controlled model/tool-call and embedding outputs for repeatable HTTP integration tests. Separately demonstrate actual LLM routing/generation; a stubbed test alone does not prove model behavior.

4. Minimum scenarios: exact structured lookup; preference-driven hybrid recommendation plus PostgreSQL eligibility; reference questions over each of the two reference families. Both search engines must run on the hybrid path, not on every query.

## Dependencies and phase

Pilot: final connected result. PY-020 and PY-022 pilot slices; PY-019 tracing; prepared source corpus. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/connected-search-pilot/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

No full UI, SSE/token streaming, chat persistence, authentication, production deployment or exhaustive regression dataset.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
