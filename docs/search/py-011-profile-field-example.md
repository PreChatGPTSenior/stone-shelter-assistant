# PY-011 Profile search document: field example

- Date: 2026-10-31
- Tracking: [PY-011](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14)
- Status: Discussion example; field names, ID convention, and revision rules are proposals, not implemented schemas
- Accepted routing/filter decisions: [Search documents and query routing](py-011-search-documents.md)
- Source example: [Velvet Slate registration request](../../fixtures/stones/af5f85d4-9cc7-48a9-a1e6-aad5d8fec581.json)

## Start here

We take one existing profile and make two searchable copies of it:

| Place | What is stored | Why |
| --- | --- | --- |
| PostgreSQL | Original stone, profile, and case rows | Authoritative business data |
| Typesense | Readable profile text plus identifiers and filters | Lexical search |
| Qdrant | An embedding of that profile text plus the same identifiers, text, and filters | Semantic search |

This example is one profile document, not the complete stone history. The stone biography and each event become separate search documents. The profile's text is assembled from existing fields with labels; no LLM summary or new pet facts are generated.

## 1. Values read from PostgreSQL

The committed request file illustrates the source values; it is not a dump of the current database. During indexing we read the persisted rows and their current state.

| Source row | Field | Example value |
| --- | --- | --- |
| Stone | external_id | af5f85d4-9cc7-48a9-a1e6-aad5d8fec581 |
| Stone | name | Velvet Slate |
| Stone | stone_type | SLATE |
| Stone | stone_size | MEDIUM |
| StoneProfile | socialization_traits | PREFERS_SOLITUDE, NEEDS_SLOW_INTRODUCTION |
| StoneProfile | care_level | INTENSIVE |
| StoneProfile | health_notes | A recurring surface crack needs close attention. |
| StoneProfile | trigger_notes | Distressed by loud music. |
| StoneProfile | preferred_environment | A peaceful home with an experienced caregiver. |
| ShelterCase | external_id | 657a88e9-880b-4dfd-9b17-4d5518fb0d16 |
| ShelterCase | case_number | 0005-2026-P1 |
| ShelterCase | adoption_status | RETURNED |
| ShelterCase | current_shelter_id | b222288c-1da8-4932-a7eb-75a55be41b87 |

Existing PostgreSQL rows also have internal IDs and technical fields. This example does not propose a new PostgreSQL SearchDocument table or alter the ORM entities. The profile is joined to its stone through its existing stone_id; the case supplies the current filter state.

## 2. Field dictionary for this profile document

All fields below are required for the proposed profile representation. Required here means required in this search document, not in an incoming registration request. Other document kinds need their own conditional field rules.

| Field | Logical type | What it means |
| --- | --- | --- |
| id | UUID, serialized as a string | Identity of this searchable profile document in both engines |
| document_kind | Enum | profile; identifies the evidence unit |
| title | Nonempty string | Human-readable result heading |
| text | Nonempty string | Labeled source facts used for text matching and embedding input |
| language | String | en, the document language |
| source_key | String | Stable logical source identity: profile followed by the stone external UUID |
| stone_external_id | UUID | Resolve/group results for the actual stone |
| case_external_id | UUID | Resolve the stone's lifetime case |
| case_number | String | Preserve the human-readable case reference |
| stone_type | StoneType | Exact type filter, copied from Stone |
| stone_size | StoneSize | Exact size filter, copied from Stone |
| adoption_status | AdoptionStatus | Current state filter, copied from ShelterCase |
| current_shelter_id | UUID | Existing current shelter reference/filter |
| schema_version | Positive integer | Version of the search document's field structure |
| projection_version | Positive integer | Version of the rules that construct text and metadata |
| source_revision | SHA-256 fingerprint string | Detect changes in source values used by this projection |
| content_hash | SHA-256 fingerprint string | Detect changes in the exact embedding input |

source_path and section_path do not apply to this database-backed profile. Event identifiers, event type, and occurred_at belong to event documents and are omitted here. Socialization traits and care level are represented in text; additional structured filters for those properties have not been selected by this example.

## 3. Proposed ID convention

The profile has no external UUID of its own. Its source_key is:

```text
profile:af5f85d4-9cc7-48a9-a1e6-aad5d8fec581
```

The proposed searchable id is a deterministic UUIDv5, not the profile's internal database primary key. For this example, UUIDv5 with NAMESPACE_URL and this full name produces the displayed ID:

```text
urn:stone-shelter:search-document:profile:af5f85d4-9cc7-48a9-a1e6-aad5d8fec581
```

The namespace and name convention are proposed here for discussion. Once accepted, they must stay fixed across engines and reindexing. Do not include current status, text hash, or embedding model in the logical document ID. Updating a profile should update the same document, not generate unrelated identities.

External stone/case UUIDs are the proposed source links so rebuilding a clean database does not change these references. current_shelter_id follows the existing source contract's seeded shelter UUID. These choices do not change any PostgreSQL primary keys.

## 4. Typesense document

Proposed collection name: search_documents_v1. This is the document body, not a collection-creation request. Hash values are placeholders, not computed SHA-256 values.

```json
{
  "id": "0e38233b-9af8-531a-a25e-abc3a34f686b",
  "document_kind": "profile",
  "title": "Velvet Slate — individual profile",
  "text": "Socialization traits: Prefers solitude; Needs slow introduction.\nCare level: Intensive.\nHealth notes: A recurring surface crack needs close attention.\nTrigger notes: Distressed by loud music.\nPreferred environment: A peaceful home with an experienced caregiver.",
  "language": "en",
  "source_key": "profile:af5f85d4-9cc7-48a9-a1e6-aad5d8fec581",
  "stone_external_id": "af5f85d4-9cc7-48a9-a1e6-aad5d8fec581",
  "case_external_id": "657a88e9-880b-4dfd-9b17-4d5518fb0d16",
  "case_number": "0005-2026-P1",
  "stone_type": "SLATE",
  "stone_size": "MEDIUM",
  "adoption_status": "RETURNED",
  "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87",
  "schema_version": 1,
  "projection_version": 1,
  "source_revision": "sha256:<source-snapshot-hash>",
  "content_hash": "sha256:<embedding-input-hash>"
}
```

Typesense uses strings for UUIDs and enum values, string fields for title/text, and integer fields for the two numeric versions. Search uses title/text; exact filtering uses the selected metadata fields. The collection schema will explicitly configure fields and indexes in a later implementation ticket. Fingerprints are stored for bookkeeping, not full-text matching.

If this collection also holds encyclopedia sections, stone-specific fields must be optional at the collection level because they do not apply to reference documents. Our profile-document contract can still require them.

## 5. Qdrant point

Qdrant wraps the same document as an id plus a vector and payload. The ID is at point level, so this example does not duplicate it inside payload.

The three numbers below are invented solely to show the structure. They are not an actual embedding. The real vector length and distance metric depend on the explicitly selected model; no model or three-dimensional index is selected by this example.

```json
{
  "id": "0e38233b-9af8-531a-a25e-abc3a34f686b",
  "vector": [
    0.12,
    -0.07,
    0.31
  ],
  "payload": {
    "document_kind": "profile",
    "title": "Velvet Slate — individual profile",
    "text": "Socialization traits: Prefers solitude; Needs slow introduction.\nCare level: Intensive.\nHealth notes: A recurring surface crack needs close attention.\nTrigger notes: Distressed by loud music.\nPreferred environment: A peaceful home with an experienced caregiver.",
    "language": "en",
    "source_key": "profile:af5f85d4-9cc7-48a9-a1e6-aad5d8fec581",
    "stone_external_id": "af5f85d4-9cc7-48a9-a1e6-aad5d8fec581",
    "case_external_id": "657a88e9-880b-4dfd-9b17-4d5518fb0d16",
    "case_number": "0005-2026-P1",
    "stone_type": "SLATE",
    "stone_size": "MEDIUM",
    "adoption_status": "RETURNED",
    "current_shelter_id": "b222288c-1da8-4932-a7eb-75a55be41b87",
    "schema_version": 1,
    "projection_version": 1,
    "source_revision": "sha256:<source-snapshot-hash>",
    "content_hash": "sha256:<embedding-input-hash>"
  }
}
```

The collection's vector dimensions and distance metric are configured separately. We will also create appropriate payload indexes for fields used in filtering, including enum/keyword fields and UUID references. Merely storing a payload field does not mean an efficient filter index was created.

The lexical and semantic branches return the same logical document ID, so Python can deduplicate and fuse their results. The payload text lets us return the original evidence and assemble model context; vector similarity operates on the vector, not automatically on that string.

## 6. Exact text sent to the embedding model

Proposed rule: title, two line breaks, then text. Filters, UUIDs, hashes, and technical versions are excluded.

```text
Velvet Slate — individual profile

Socialization traits: Prefers solitude; Needs slow introduction.
Care level: Intensive.
Health notes: A recurring surface crack needs close attention.
Trigger notes: Distressed by loud music.
Preferred environment: A peaceful home with an experienced caregiver.
```

Record the embedding model/revision, dimensions, distance metric, and preprocessing in vector-index/experiment configuration. They are properties of the vector representation, not new business fields on StoneProfile. A later model change can require new vectors without changing the logical document ID.

## 7. Why four revision fields exist

| Field | Changes when | Does not tell us |
| --- | --- | --- |
| schema_version | We change the document structure/contract | Which business update is newer |
| projection_version | We change text rendering or metadata-construction rules | Which source snapshot is newer |
| source_revision | Any selected source dependency changes, including current filters | Chronological ordering; a hash is not a sequence number |
| content_hash | The exact title-plus-text embedding input changes | Which embedding model generated the vector |

Canonical source serialization, text normalization, and exact hashing rules must be agreed before implementing these fields. Do not claim the example's placeholder hashes are usable values. An ORM version on one row is not a version of a projection assembled from multiple rows. Preventing stale background work from overwriting newer index state requires a separately designed ordering mechanism.

## 8. Three update examples

| Change | PostgreSQL | Typesense | Qdrant |
| --- | --- | --- | --- |
| Case becomes AVAILABLE | Update the case through its accepted business operation | Update status metadata and source_revision on affected documents | Update payload status and source_revision; reuse the vector if embedding input is unchanged |
| Staff change trigger notes | Update the profile | Rebuild text and fingerprints | Rebuild text/fingerprints and generate a new vector |
| Reindex unchanged source with the same rules/model | Preserve business rows | Reuse the same ID and content | Reuse the same ID and compatible vector |

The current example remains RETURNED. It can appear in historical/case searches, but an AVAILABLE recommendation filter excludes it. Before an actionable recommendation, verify current eligibility and shelter responsibility in PostgreSQL. A stale-negative index filter can still miss a candidate; final verification does not repair all retrieval misses.

## 9. What is deliberately not included

- No copying of the full ORM graph or all five events into this profile document.
- No invented suitability conclusions, generated summary, or conversion of missing facts into positive claims.
- No embedding in the initial lexical Typesense document.
- No query score, rank, or highlights in the stored source document; those belong to a query result.
- No source-generated technical IDs, timestamps, or concurrency rules inferred from these examples.
- No engine setup, new application/test code, indexing job, or model call is implemented by this document.
