# PY-022 design boundaries

## Current evidence

Reviewed on 2026-11-08. No LangGraph dependency, graph, tool contracts or routing implementation exists. The pilot must include actual LLM tool choice, not only a fixed graph. No application tests or model calls were run for this documentation audit.

## Responsibilities and decisions

1. Initial tools: exact candidate lookup; hybrid candidate/evidence search; reference search with a source-family selector (encyclopedia/type compatibility); stone details/history lookup. Reuse existing application operations, not raw database clients exposed to the model.

2. Use a typed graph state containing question, explicit constraints, selected calls, tool outputs/evidence, checked candidates, answer and trace reference. Validate structured arguments before execution.

3. A bounded model tool-call round may select more than one relevant tool; execute it, assemble evidence and answer. Make maximum calls/rounds explicit. No unbounded autonomy or mandatory call to every engine.

4. The model chooses application purpose; hybrid backend strategy is deterministic in PY-018 initially. Choosing lexical versus vector versus hybrid is a later experiment.

5. Hard filters and final availability checks remain application-controlled. Later clarification may ask about ambiguity, never silently relax explicit constraints. Do not introduce mutation tools.

## Dependencies and phase

Pilot slice, then post-pilot extension. PY-014, PY-018, PY-019 pilot and reusable answer composition from PY-020. See the central delivery plan for ordering; ticket numbers are identities, not execution order.

## Verification strategy

Use the scenarios in specs/tool-routed-langgraph/spec.md and the focused tasks checklist. Test database/engine adapters with disposable Testcontainers and explicit settings. Keep live inference separately invoked; source-authoring review is not an instruction to create framework-mirroring tests. Do not claim acceptance based only on artifact validation.

## Deferred work

Free-form SQL, lifecycle mutations, unbounded loops and production agent recovery are excluded.

## Authority

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.
