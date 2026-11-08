# ADR-0017 Prepare all sources first and include LLM tool selection in the pilot

> Current source amendment: [ADR-0018](0018-json-compatibility-and-deferred-tarot.md) replaces Markdown compatibility/sample coverage with an authored complete JSON guide and removes the astral catalog from the pilot. Tarot is a separate deferred idea. Earlier source-priority wording below records decision history.

- Status: Accepted owner decision; planning only, implementation remains pending
- Date: 2026-11-08
- Supersedes: earlier deferral of astral source creation and a fixed-only first-result milestone
- Related: [manifesto](../project-manifesto.md), [ADR-0016](0016-typesense-lexical-qdrant-vector-experiments.md), [delivery plan](../search/pilot-delivery-plan.md)

## Context

The owner approved the reviewed search backlog and asked for an OpenSpec change for every remaining task. Before retrieval integration, prepare the operational examples and all reference sources: the existing encyclopedia, fictional type compatibility, and a fictional astral catalog. This moves source authoring forward, without moving sophisticated evaluations or production infrastructure into the pilot.

## Decision

1. First review/reuse the operational JSON corpus and encyclopedia, then author the compatibility and astral documents and complete the source inventory. Keep this small and sufficient for concrete supported questions; no exhaustive matrix or large benchmark dataset is required.
2. Next finish shared evidence preparation, including distinct citeable source identities for all three reference families. Do not duplicate individual availability or shelter fields onto reference documents.
3. Feed Typesense lexical retrieval and Qdrant vector retrieval directly from prepared evidence. JSONL is not an application storage/interchange prerequisite. Optional reproducibility snapshots belong to later experiment tooling.
4. PostgreSQL remains authoritative for exact structured lookup and final current-state verification. Source adoptionStatus and current shelter are not reconstructed from events. Textual candidate search uses the same explicit hard filters in both indexes.
5. The first connected pilot includes actual LLM request interpretation and typed tool calls inside a bounded LangGraph. A fixed answer chain is useful reusable composition and a later comparison baseline, but it does not alone satisfy this milestone.
6. Start with application tools for exact candidates, hybrid candidates/evidence, reference retrieval by source family, and individual details/history. The model need not choose raw database technologies. Mandatory constraints and final availability checks remain deterministic application behavior.
7. Use LangChain for tools/model composition, minimum useful Langfuse tracing and one selected tool-capable model/provider first. Ollama and OpenRouter both remain accepted targets; complete provider comparisons and budget accounting follow the pilot. Explicit finite call/output/context limits apply immediately.
8. Deliver a minimal question/answer HTTP entrypoint with sources and trace references. Verify real retrieval with controlled inference in Testcontainers tests and separately demonstrate real model tool calls. Live inference is not part of make check.
9. After that, establish the measured baseline and evaluation harness, then iterate on reranking, representations, models, languages, richer graph behavior, index freshness, backend comparisons and Spring AI.

## Source boundaries

Compatibility and astral content are authored fictional world guidance. Exact creative rules are decided during source writing, not invented by this plan. Existing rock types suffice initially; no individual birth dates, signs, extra input fields or ORM schema changes are required. Reference guidance cannot override individual observations or authoritative current availability.

## Tracking and delivery

The delivery plan maps existing GitHub tickets to local OpenSpec changes and records new local planning IDs separately. Creating documentation does not create GitHub issues, update board states, complete implementation, archive changes or authorize a commit. Source content is the first implementation-stage work; it is not authored in this documentation-only pass.

## Consequences

The first pilot has a slightly richer corpus and real tool routing, while remaining a small happy-path learning application. Existing Typesense infrastructure and encyclopedia preparation are reused. All future tasks have reviewable requirements and unchecked implementation tasks; selected pilot and post-pilot slices remain explicit. README files, application code, test code, dependencies, data and running services remain untouched by this planning change.
