# ADR-0016 Use Typesense for lexical retrieval and Qdrant for vectors

- Status: Accepted architecture and experiment plan; not connected or implemented
- Date: 2026-10-30
- Related: [ADR-0006](0006-rag-and-agent-learning-focus.md), [ADR-0004](0004-postgresql-task-queue.md), [domain model](../domain/model.md)
- Requirements: [RAG learning requirements](../requirements/rag-learning.md), sections 7.1 and 8.6

> Sequencing clarification (2026-11-05): the [project manifesto](../project-manifesto.md) and [pilot plan](../search/pilot-delivery-plan.md) narrow the first implementation to one connected happy path. Evaluation datasets/harnesses, reranking, synchronization, recovery, and broad agent/backend comparisons below are post-pilot experiments. Minimum useful Langfuse tracing and a minimal LangGraph flow belong to the pilot. The selected engine architecture is unchanged.

## Context

The owner already has extensive Java/Solr search experience. The objective is to learn Python AI engineering, hybrid retrieval, flexible tools, agentic RAG, evaluation, and observability rather than spend the next increment tuning a familiar search engine.

PY-010 provides an HTTP registration path, a persistent PostgreSQL source database, ten reusable stone requests, profiles, lifetime cases, and life events. The encyclopedia is another existing source; fictional type compatibility and the deferred astral catalog remain distinct planned sources. Search engines, embeddings, LangChain/LangGraph runtime, and provider/tracing integrations are not implemented by this decision.

## Selected responsibilities

| Component | Responsibility | Implementation status |
| --- | --- | --- |
| PostgreSQL | Authoritative operational records, current availability, shelter responsibility, and durable indexing intent when asynchronous indexing is introduced | Business persistence implemented; indexing intent deferred |
| Typesense | Initial lexical retrieval, text matching, filtering, and independently inspectable lexical candidates | Selected, not connected |
| Qdrant | Initial vector retrieval over externally generated embeddings and metadata | Selected, not connected |
| Python retrieval pipeline | Common document identities, orchestration, deduplication, rank fusion, grouping, optional reranking, and evidence assembly | Planned |
| LangChain | Retrieval/model/tool integration and composition | Accepted learning target; not connected |
| LangGraph | Explicit agent state, routing, clarification, bounded repeated retrieval, and recovery | Accepted learning target; not connected |
| Langfuse Cloud Hobby | Traces and experiment diagnostics alongside local versioned results | Previously selected; not connected |

Solr is not selected for this increment. pgvector is deferred as a possible future comparison backend, not required in parallel with Qdrant. The existing pgvector-capable PostgreSQL image does not mean vector search is already configured. Typesense's vector/hybrid features are a later optional comparison, not the initial selected vector backend.

## Search document and indexing boundaries

- Produce a common, versioned set of search documents from operational records and reference sources. Search documents are derived representations, not replacement business entities.
- Preserve stable document/chunk IDs and stone, case, event, source, section, and version references where applicable. Lexical and vector indexes must be able to refer to the same evidence units.
- Choose document granularity explicitly before indexing: profile, event, and reference section are candidates to evaluate. Do not silently compare full-stone documents in one branch with isolated fragments in another.
- Generate embeddings in Python and send them to Qdrant. Record model, revision, dimensions, distance metric, preprocessing, chunking, and corpus version. Built-in embedding or conversational features must not hide the steps being studied.
- Retain source text and provenance so recommendations can cite actual evidence and fetch the authoritative source when needed.
- Index metadata for retrieval filters, but verify current availability and shelter responsibility against PostgreSQL before final recommendations. A stale index cannot redefine current business state.
- Search indexes must be rebuildable from authoritative source data. Initial experiments can use explicit full reindex commands; exact command/API design is not decided here.
- When automatic asynchronous indexing is introduced, preserve business writes and durable indexing intent in the same PostgreSQL transaction under ADR-0004. External engine writes and model calls do not participate in that database transaction. Delivery, retries, source versions, and recovery are separate implementation work.
- Typesense and Qdrant introduce independently updated indexes. Test and trace stale, missing, and partially refreshed data rather than assuming a distributed atomic write.

## Accepted experiment plan

Run comparable experiments incrementally, not all infrastructures and variations at once.

| Stage | Comparison | Main question |
| --- | --- | --- |
| Baselines | Structured SQL lookup; direct model; full relevant context when it fits | Is retrieval or agent orchestration needed for this case? |
| Independent retrieval | Typesense lexical versus Qdrant dense-vector search | Which relevant evidence and candidates does each branch miss? |
| Cross-engine hybrid | Parallel lexical/vector retrieval, Python rank fusion, deduplication, and grouping | Does combining complementary result lists improve retrieval? |
| Fusion tuning | RRF first; vary per-branch candidate counts and weights; evaluate alternatives explicitly | Which combination helps on held-out cases? |
| Reranking | Hybrid candidates with and without a separate reranker | Does extra ranking improve evidence/candidate order enough to justify latency and cost? |
| RAG workflow | Fixed retrieval/generation pipeline versus bounded agent-selected retrieval | When does choosing tools, rewriting, clarifying, or searching again improve results? |
| Representations | Chunking strategies, embedding models, language handling, multiple representations | Which representation improves the actual task? |
| Failure/freshness | One branch unavailable, timeouts, stale availability, and newly appended evidence | Is recovery bounded and are results still truthful? |
| Optional engine comparison | Typesense vector-only; Typesense built-in hybrid; Typesense lexical plus Qdrant vectors | What changes with the backend or built-in fusion when inputs are held constant? |
| Later extension | pgvector or Solr as alternative adapters only for a concrete comparison | Does another backend answer a question not covered by the initial pair? |

RRF is the initial planned fusion method, not an implemented component. Do not add raw lexical scores to vector similarity/distance without explicitly addressing scale and direction. Preserve component ranks/scores and identify their meanings. A separate cross-encoder reranker is not the same experiment as vector-based rescoring.

For the optional Typesense vector comparison, reuse identical externally generated vectors, document IDs, metadata, filters, and distance metrics where supported. Do not generate new embeddings and attribute the difference to the database. For built-in hybrid versus Python fusion, record differences in fusion algorithms rather than labeling every difference an engine-quality effect.

## Vector-store comparison discipline

With the same vectors, metric, and filters, exact nearest-neighbor results should agree apart from ties and numeric differences. A different database does not itself improve embedding semantics.

Evaluate approximate-search recall against exact search separately from semantic relevance against human-reviewed labels. Relevant engine-level variables include ANN settings, selective filters, quantization, memory, latency distributions, updates, and support for multiple vector representations. Qdrant named vectors and multi-stage queries are future exercises, not requirements for the first dense-search implementation.

Ten stones are sufficient to exercise the end-to-end flow, not to claim meaningful ANN scalability or latency advantages. Expand the corpus for performance studies; use curated difficult cases and distractors for relevance studies. Change one controlled factor at a time.

## Agent and tool experiments

- Start with bounded typed tools for structured candidate lookup, evidence retrieval, full history lookup, encyclopedia search, and fictional compatibility lookup as those sources become available.
- Begin with explicit retrieval configuration. Later compare a single search tool using fixed hybrid retrieval with a model that chooses lexical, semantic, or hybrid strategies. Exposing every backend as a tool is an experiment, not a prerequisite.
- Study query decomposition, query rewriting, parallel retrieval, insufficient-evidence detection, clarification, and useful repeated search.
- Keep mandatory constraints deterministic. The agent may propose relaxation of soft preferences but must not silently weaken hard filters or make adopted/reserved/returned pets available.
- Trace observable tool choices and execution outcomes; do not claim access to hidden model reasoning.
- Bound calls, retries, loops, context, elapsed time, and monetary spend. An unavailable engine or absent evidence must not be replaced with invented facts.
- Keep profile observations, historical events, encyclopedia guidance, fictional compatibility rules, and the future astral catalog distinguishable. Missing profile information means unknown.

## Evaluation and observability

Version the dataset, corpus snapshot, source/index versions, embeddings, preprocessing, chunking, retrieval/fusion/reranking configuration, prompts, model/provider settings, and application revision.

Measure retrieval relevance and candidate suitability separately from answer quality. Track recall@k, precision@k, ranking metrics when useful, hard-constraint violations, grounding, citation correctness, uncertainty, tool/argument correctness, useful versus unnecessary repeated retrieval, errors, latency, tokens, and cost. Separate ANN neighbor recall from relevance recall; distinguish fragment-level and stone-level results.

Use human-reviewed relevance judgments and held-out cases. LLM-as-judge is an explicitly invoked, calibrated later experiment, not the sole reference. Record candidate/evidence IDs, lexical/vector ranks and scores, fusion results, reranker output, exclusions, graph branches, budgets, and trace IDs. Local experiment artifacts remain available independently of hosted trace retention.

Existing Ollama, OpenRouter, Langfuse, and budget decisions remain unchanged. Ordinary make check must not invoke live models or paid evaluation calls. Later Spring AI comparisons should reuse the same documents, vectors where practical, queries, judgments, and behavioral constraints. A framework VectorStore adapter must not be assumed to expose the full lexical or hybrid API.

## Implementation boundary

This ADR authorizes documentation of the choices and plan only. It does not add dependencies, Docker services, credentials, collections, indexes, workers, embeddings, provider calls, tracing exports, or application code. Backend versions, clients, schemas, query contracts, index freshness behavior, and first implementation ticket remain to be designed explicitly.

## References

- [Typesense vector and hybrid search](https://typesense.org/docs/30.2/api/vector-search.html).
- [Qdrant hybrid and multi-stage queries](https://qdrant.tech/documentation/search/hybrid-queries/).
- [Qdrant points and named vectors](https://qdrant.tech/documentation/manage-data/points/).
- [pgvector](https://github.com/pgvector/pgvector), deferred comparison backend.
- [Spring AI Typesense VectorStore](https://docs.spring.io/spring-ai/reference/api/vectordbs/typesense.html).
