# Pilot evidence preparation design

## Context and authority

The manifesto narrows the accepted ADR-0016 experiment architecture to the first connected result. PostgreSQL remains authoritative. docs/domain/model.md and ADR-0015 forbid history-derived current adoption status or shelter.

## Evidence units

Use one document per stone, present profile, and case event. Reference documents are independent of any individual case. Preserve original facts; render structured profile fields with readable labels rather than generating LLM summaries or missing facts.

Operational metadata includes external stone/case identity, case number, type, size, current status, and current shelter. Apply the same explicit filters to lexical/vector branches later; exact requests can use PostgreSQL. Recheck current state before final recommendations.

Encyclopedia pilot proposal: ten whole rock-type chapters plus four general sections, split at top-level Markdown headings with nested headings/caveats retained. Skip navigation, preserve source path and section identity. Inspect actual output and model input limits before finalizing finer chunking. No general Markdown parsing framework is needed for the known input.

## Organization

The existing local search/documents.py models and search/enums.py are draft shared evidence representations, not transport DTOs or engine schemas. Suggested search/encyclopedia.py is a pure function from Markdown text/source path to document models; tools/export_encyclopedia.py handles file I/O and JSONL inspection. Neither suggested file exists yet.

Use deterministic source identities and straightforward hashes sufficient for repeatable pilot output. Keep the current model fields without expanding them into schema migration, revision ordering, or synchronization infrastructure. Exact final conventions remain subject to inspecting generated data.

## Later work

Projection/indexing continues in PY-013. Embeddings, Typesense/Qdrant adapters, retrieval, and LangGraph follow the pilot plan. PY-017 owns reviewed evaluation datasets after the first result. Benchmarking, reranking, retries, partial failures, and freshness recovery do not gate this change.

## Evidence boundary

The reconciliation branch contains documentation only. Local PY-011 models were inspected, but export and index integrations are not implemented. No new test result or provider execution is claimed.
