# PY-011 Search documents and query routing

- Status: Evidence models and encyclopedia preparation exist locally; operational/new reference preparation and retrieval remain pending
- Date: 2026-10-30
- Tracking: [PY-011](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14)
- Related: [Domain model](../domain/model.md), [ADR-0016](../adr/0016-typesense-lexical-qdrant-vector-experiments.md), [RAG learning requirements](../requirements/rag-learning.md)

## Scope

Define the search representation and routing boundaries before implementing Typesense lexical retrieval and Qdrant vector retrieval. This document records decisions, not installed or working search capabilities. It does not change the operational entities or incoming registration contract.

## Worked field example

See [one profile across PostgreSQL, Typesense, and Qdrant](py-011-profile-field-example.md) for a separate field-by-field discussion example. Its proposed field names, ID convention, and revision rules are not yet finalized contracts.

## Source of truth and search projections

PostgreSQL remains authoritative for operational records, including the source-provided current adoption status, stone properties, and current shelter assignment. Search indexes contain derived, rebuildable projections that support retrieval and filtering.

The initial evidence units are one stone document, one document per existing profile, one document per case event, and one meaningful reference section. Reference families include the encyclopedia, authored JSON type compatibility under ADR-0018; use these sources, then prepare them in PY-011. An absent profile produces no profile document; missing data must not become invented positive claims. Preserve parent identities and source references so retrieved evidence can be grouped by stone and cited.

## Primary filtering strategy

Store the operational fields required for candidate filtering in the search indexes as metadata. Apply the same logical hard constraints to both the Typesense lexical branch and the Qdrant vector branch before combining candidates.

For operational evidence documents, the agreed filtering metadata includes:

| Field or reference | Purpose | Authoritative origin |
| --- | --- | --- |
| Stone identity | Group evidence and resolve the actual candidate | Stone |
| Stone type | Exact type restriction | Stone.stone_type |
| Stone size | Exact size restriction | Stone.stone_size |
| Current adoption status | Restrict by current case availability/state | ShelterCase.adoption_status |
| Current shelter identity | Restrict by responsible shelter | ShelterCase.current_shelter_id |
| Document kind, source, and version | Select evidence sources and diagnose freshness | Source record/document and projection metadata |

These fields are a deliberate denormalization for retrieval, not a second business source of truth. Copy only fields required for search, filtering, provenance, and result resolution; do not mirror the complete ORM graph into every document.

Current status is distinct from a historical event type. An ADOPTED event may belong to a currently RETURNED case; do not use the event type to reconstruct or replace current status. Index metadata comes from the current source snapshot.

Encyclopedia sections do not belong to an individual stone. They can carry rock type, section, source, and version, but not an individual's adoption status, size, or shelter assignment. Search reference knowledge separately where necessary rather than applying individual-candidate filters to general documents.

Exact metadata field names, internal versus external identity representation, and index schema declarations remain contract details to finalize. The table defines meanings and ownership, not executable schemas.

## Query routing

| Intent | Primary path | Example |
| --- | --- | --- |
| Exact operational lookup or filtering without a text-matching need | Typed PostgreSQL query | "Show small granite stones." |
| Textual or semantic matching plus optional exact constraints | Hybrid retrieval, with applicable metadata filters in both indexes | "Find a small granite stone that would suit a quiet home." |
| General reference question | Reference-document retrieval | "What moisture conditions are appropriate for slate?" |

- Do not invoke lexical/vector retrieval or compute embeddings merely to satisfy an exact structured query.
- For hybrid retrieval, separate hard constraints from the searchable wording. In the example above, type and size are filters; suitability for a quiet home is a retrieval need.
- Apply filters only when stated by the user or required by an explicit use-case rule. A generic case search must not silently default to AVAILABLE.
- An available-adoption recommendation may enforce AVAILABLE as an explicit business rule. Looking up an adopted stone's case must still be possible.
- Ambiguous constraints should lead to clarification when they materially affect results. Do not silently replace hard constraints with softer preferences.
- Initial database access uses deliberate typed application operations, not unrestricted model-generated SQL.

SQL prefiltering by a list of eligible stone IDs remains a possible comparison strategy. It does not inherently remove hybrid retrieval: lexical and vector results can still be combined within that eligible set. It is not the primary selected path for text-based candidate selection.

## Current-state verification before recommendation

After retrieving and grouping candidate evidence, read the candidate records from PostgreSQL before making an actionable recommendation.

- Verify that the stone and case exist and that the current authoritative state satisfies the recommendation's hard constraints, including availability and current shelter responsibility where applicable.
- Use authoritative records for current-state claims and pickup details; use retrieved fragments for cited observations and reference guidance.
- Exclude candidates that no longer qualify. Do not present stale indexed availability as current truth or silently weaken the request.
- Report insufficient eligible candidates honestly. Whether to retrieve additional candidates is a later bounded workflow decision, not permission for an unbounded loop.

This verification protects against false-positive eligibility from stale index data. It cannot recover a candidate excluded by a stale index filter, so correct final checks do not by themselves guarantee complete retrieval.

## Index freshness and updates

- Changes to filtering fields must propagate to the affected operational search documents in both indexes. Updating a case status can affect all indexed evidence belonging to that stone/case.
- Changing filter metadata alone does not inherently require recomputing text embeddings when their input text and model remain unchanged.
- Preserve source/projection versions and expose freshness information in experiments. Exact freshness targets and operational handling remain to be designed.
- Initial explicit reindexing and later durable asynchronous delivery follow ADR-0016 and ADR-0004. Do not claim PostgreSQL and both search engines share one atomic transaction.
- Include stale-positive, stale-negative, and partially refreshed index scenarios in later evaluation. Distinguish retrieval misses from final current-state rejection.

## Boundaries and remaining decisions

Typesense infrastructure/client and encyclopedia preparation now exist locally; neither index population nor retrieval is implemented. Remaining PY-011 work is operational graph projection and preparation of the JSON compatibility reference family with concrete identities and provenance. Deliver prepared objects directly to adapters, without application JSONL export. Final universal schemas and reviewed relevance datasets are not prerequisites; evaluation follows the pilot in PY-017. See the delivery plan and OpenSpec tasks for the authoritative sequence. This document does not close tickets or authorize implementation.
