# THIS IS A LEARNING PROJECT

**HAPPY PATH FIRST. GET THE FIRST END-TO-END PILOT WORKING, THEN MEASURE AND IMPROVE.**

- Date: 2026-10-31
- Status: Owner-approved learning direction and scope boundary
- Applies until the owner explicitly changes the direction

## Purpose

Stone Shelter is a hands-on Python AI engineering laboratory set in a fictional world where stones are pets. Its purpose is to learn hybrid retrieval, LangChain, LangGraph, tool calling, Langfuse observability, metrics, and evaluation frameworks through working experiments.

The owner is an experienced Java senior engineer and architect. Familiar enterprise infrastructure and product completeness must not displace the unfamiliar AI engineering work that motivates this project.

Success means building a working first version, understanding its behavior, capturing a baseline, and learning how deliberate changes improve or worsen the results. It does not mean delivering a production-ready shelter product.

## Current priority: the first working pilot

Implement the shortest coherent happy path:

1. Prepare the source corpus first: reuse operational JSON and the encyclopedia; use the complete fictional JSON type-compatibility guide (ADR-0018); the separate tarot idea is deferred.
2. Prepare simple shared evidence documents from stones, profiles, history and both distinct reference sources: Markdown encyclopedia and JSON compatibility.
3. Index lexical documents in Typesense and generate embeddings explicitly for Qdrant; no application JSONL intermediate.
4. Connect LangChain tools and a bounded LangGraph in which the LLM actually selects typed SQL, hybrid, reference or details/history operations.
5. Produce an evidence-grounded answer through a minimal HTTP entrypoint, with explicit hard filters and final PostgreSQL current-state checks.
6. Add minimum useful Langfuse tracing and demonstrate the supported paths with a selected real model; ordinary tests keep controlled inference.

The first pilot is complete when a meaningful request runs through the real connected retrieval and model workflow and returns an evidence-based result. Typesense and Qdrant must both be exercised; not every future query has to use both. Pure structured requests can use PostgreSQL as already agreed.

Do not make an extensive query/result schema, universal document abstraction, full experiment harness, final chunking design, or exhaustive relevance dataset a prerequisite for this first result. Use small concrete examples and refine the representation after inspecting actual results.

## Happy-path assumptions

For the pilot, assume prepared source data is consistent, configured services are available, credentials and model choices have been explicitly supplied, and the chosen request follows the supported route. Missing business data still means unknown; do not fabricate facts to make a result look successful.

Do not design negative outcomes, resilience branches, or production recovery mechanisms as prerequisites. Let unexpected errors remain visible rather than swallowing them or claiming success. Existing boundary validation, database constraints, and basic resource cleanup remain in place; the happy-path scope is not permission to corrupt data or conceal failures.

## Narrow scope, high code quality

Keep the implementation idiomatic, readable, typed, and consistent with the documented domain and installed stack. Give components clear responsibilities and use the selected libraries correctly.

Quality does not require supporting every possible input, deployment, failure, or future backend now. Prefer the smallest sound implementation of the selected path. Introduce an abstraction only when it serves the current pilot or an explicitly selected learning exercise.

Keep PostgreSQL authoritative for business records. Search documents are derived representations. Preserve explicit filters, source identity, and current-state verification before actionable recommendations. Source adoptionStatus is supplied by the upstream system, not reconstructed from history.

Preserve the local application's existing data. Testcontainers remains the target for automated database tests. No implicit database reset, volume deletion, schema backfill, or legacy compatibility work is authorized by this manifesto.

## Deferred until after the pilot

The following are learning backlog items, not blockers for the first result:

- Comprehensive evaluation datasets, held-out studies, metrics dashboards, calibrated LLM judges, and a complete experiment runner.
- Multiple embedding models, elaborate chunking strategies, reranking, backend benchmarks, quantization, and additional search engines.
- Complex revision schemes, generic schema evolution, and finalized contracts for every future document and query shape.
- Durable indexing queues, outbox workers, retries, deduplication, stale-job rejection, automatic synchronization, and distributed failure recovery.
- Negative-path test matrices, injected outages, partial-write/index recovery, concurrency stress tests, and performance/load testing.
- Production deployment, high availability, multi-tenancy, authentication/roles, full UI, complete CRUD, photos/object storage, and unrelated infrastructure.
- Full agent autonomy, many routing strategies, long-running workflows, and lifecycle-writing tools.

These items are deferred, not rejected. Existing code/tests need not be removed. Existing backlog tickets describe possibilities, not a requirement to complete them before running the pilot.

## After the first result: evaluate and iterate

Capture the first working configuration and representative outputs as the baseline. Then introduce an evaluation framework and repeatable measurements incrementally.

Change one meaningful factor at a time: document granularity, chunking, embedding model, retrieval limits, filters, fusion, reranker, generation model, prompt, tools, or graph routing. Preserve comparable inputs and record results, traces, latency, usage, and cost where available.

Investigate problems observed in real runs and add targeted scenarios or failure handling when that becomes the selected learning task. Do not expand the scope in anticipation of every hypothetical failure.

The later Spring AI comparison remains a learning target after the Python path produces useful, measurable behavior.

## Working rule for every next step

Before proposing or implementing more work, state which part of the first end-to-end result it enables. If it does not enable the current pilot, put it in the later backlog rather than expanding the active task.

This manifesto takes precedence over earlier sequencing suggestions and broad acceptance criteria that would delay the pilot. It does not override the owner's explicit instructions, domain facts, data ownership, README ownership, or authorization boundaries. The owner writes learning code unless implementation is explicitly delegated.

## Related documents

- [Domain model and field ownership](domain/model.md)
- [PY-011 search documents and routing](search/py-011-search-documents.md)
- [Retrieval architecture and later experiments](adr/0016-typesense-lexical-qdrant-vector-experiments.md)
- [Learning requirements and backlog](requirements/rag-learning.md)
