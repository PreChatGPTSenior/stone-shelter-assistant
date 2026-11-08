# PY-011 evidence preparation design

## Inspected local baseline

search/documents.py defines stone/profile/event/encyclopedia Pydantic models with stable evidence IDs, provenance, hashes and schema/projection versions. search/encyclopedia.py prepares fourteen sections using LangChain MarkdownHeaderTextSplitter; its real-source scenario exists. Operational projection and compatibility JSON preparation do not exist. No application tests were run in the 2026-11-08 planning audit.

## Operational evidence

Use one stone document, one per existing profile and one per event. Read persisted records with explicitly loaded relationships; avoid implicit async lazy database access. Render stored values with readable labels without model summarization or fabricated facts. A missing profile yields no profile document; an empty/unknown attribute is not a suitability claim.

All operational documents share external stone/case IDs and copy current type, size, adoption status, current shelter and case number. Event identity and occurred_at describe historical evidence; never derive current state from event ordering or timestamps. Preserve names and immutable source identities separately from internal database UUIDs.

Define deterministic source keys for each kind: stone/profile use the external stone identity, events use external event identity. Reuse the existing UUIDv5 urn convention. Document the precise rendered text/hash inputs as implemented; keep schema/projection version 1 until an actual representation change. Source revision and content hash are diagnostic evidence, not a transactional graph-version service.

## Reference evidence

Reuse the fourteen encyclopedia sections, including nested headings and qualifications. PY-028 supplies the authored JSON source. Extend reference document kinds/models deliberately to identify compatibility pair entries separately; do not label all knowledge encyclopedia or split JSON with MarkdownHeaderTextSplitter. Decide their concrete metadata from the authored sources, without new ORM fields.

Each reference unit carries stable source-family identity, path, section and text. Each JSON pair entry identifies both types and declares symmetric applicability through the catalog coverage rules; preserve its entry ID and edition, and do not force the pair into the encyclopedia's single optional stone_type field. No individual's adoption status, size or current shelter appears on general guidance.

Start with one meaningful encyclopedia section or JSON pair entry per reference evidence unit. Later PY-015 verifies actual model limits and introduces explicit finer splitting only if necessary. Source-specific preparation functions are sufficient; no generic ingestion framework.

## Direct handoff

Preparation returns document objects. PY-013 serializes them to Typesense; PY-015/PY-016 use the same IDs and text for vectors and Qdrant. Do not require an intermediate JSONL file. Experimental corpus snapshots belong to PY-017 later.

## Verification and boundaries

Use a focused scenario reading a stored registration graph from Testcontainers, checking useful source identity, current-state metadata and absent-profile behavior. Inspect actual reference outputs with their source passages. Avoid duplicated tests of every Pydantic field or fixture. Existing encyclopedia tests stay in place.

The owner-approved source-first order in ADR-0017 supersedes older export and final-schema prerequisites. docs/domain/model.md and ADR-0015 own field/state semantics. Typed quality is required; exhaustive negative paths, revisions, queues and measured relevance are later work.
