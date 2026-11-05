# ADR-0008 External batch creation and single-stone partial updates

- Status: Partially superseded; single-record registration implemented, later mutations deferred
- Date: 2026-10-29
- Refines: [ADR-0006](0006-rag-and-agent-learning-focus.md) and [ADR-0007](0007-lifetime-shelter-case-identity.md)
- Requirements: [External ingestion contract](../requirements/rag-learning.md#33-external-ingestion-contract)

> Reconciled 2026-11-05: ADR-0013 supersedes multi-stone batch registration; ADR-0015 requires source-provided adoptionStatus without replay; ADR-0014 separates persistent application data from disposable tests. Snapshot registration, shelter references, and source identity are implemented through PY-010. Partial updates, ordering/no-op replay, and new history endpoints remain future work; historical text below must not be used as the current payload contract. See the [current domain contract](../domain/model.md) and [pilot plan](../search/pilot-delivery-plan.md).

## Context

The next domain increment establishes entities and representative data before designing search. An external service sends specimen and accounting data to the hub. JSON fixtures and a sending script simulate that service through our API. The owner does not want a public manual-entry workflow, physical deletion, or implementation of the entire upstream accounting system.

## Decision

### Operations and sequence

Provide two integration operations: batch creation and partial update of one stone's associated record. Exact route names and request/response schemas will be designed with the entities; they are not fixed here.

Create the basic entities and seed data first. Search behavior, ranking and retrieval policy will be discussed afterwards. [ADR-0009](0009-fictional-pet-stone-profiles.md) accepts the additional fictional profile concepts; their precise vocabulary and payload fields remain to be finalized.

### Shelters

Represent Shelter as a simple database entity, initially populated with two records. Each record has an identifier, name and address. Shelter is a location/accounting reference used by ShelterCase, not a Python enum containing operational address data. Coordinates, distance search, shelter administration UI and a separate shelter-management API are not required now. The exact identifier convention used by upstream requests remains to be specified.

### External identities

The upstream service supplies a stable UUID for the physical Stone. Preserve it as an externally assigned unique integration identifier; it is not a relational foreign key merely because another system generated it. The hub may use a separate internal database primary key, but that key strategy is not mandated by this decision. Do not generate a new external identity on repeated delivery.

Retain the distinct externally assigned ShelterCase UUID and immutable unique searchable case number from ADR-0007. Stone identity, case identity and display case number have separate responsibilities. A return or transfer does not change them.

The existing PY-003 creation endpoint generates Stone UUIDs locally. That historical behavior is implemented, but it is not the desired identity contract for the future external ingestion operations. Do not silently rewrite the old behavior through documentation alone.

### Partial updates and duplicate detection

An update targets one known stone and includes only changed fields. Omitted fields retain their current values. Define the meaning of explicit null, immutable fields, nested case updates, and collection replacement when the concrete DTO is designed; partial update does not authorize clearing omitted data.

Use an upstream change timestamp to compare deliveries and avoid an older update overwriting newer accepted state. Compare incoming business data with the effective stored state after applying the supplied fields. A replay with unchanged effective business data is a no-op: it must not create duplicate entities, redundant business-history entries, or unnecessary reindexing work.

The timestamp is supplied by the source, not our receipt time. Its field name, timezone/precision contract, handling of equal timestamps with different data, and watermark advancement for newer timestamps with unchanged content remain open. Do not imply that timestamp ordering is a complete exactly-once or concurrency solution.

### History and trust boundary

The hub records observed business changes itself. It does not require the source to send a complete history. Record meaningful before/after changes, source time and receipt time as appropriate when the history format is defined. Do not fabricate unobserved intermediate transitions between snapshots or partial deliveries.

Assume the upstream service has already enforced business consistency. Do not rebuild its complete validation and workflow engine in the ingestion layer. This assumption does not eliminate JSON/type/format validation, identity and reference checks, or timestamp ordering needed to store and relate records correctly. How to report violations of the assumed contract remains open.

The four statuses and business transitions in ADR-0007 describe domain semantics, while the importer receives externally established state. Initial ingestion may represent an already reviewed, reserved or adopted stone rather than replaying an entire lifecycle. Detailed snapshot/transition validation policy is not decided here.

### No physical deletion

Stones and their lifetime cases are retained. Changes in availability are represented through case state/history, not DELETE. The earlier plan for the owner to implement a Delete endpoint is superseded; no Delete operation is planned for this integration. Any future archival or withdrawal semantics require a separate decision, not an invented status in this ADR.

## Consequences and open details

- The model can be designed now without first resolving search behavior or every future playful property.
- Define batch atomicity, per-item errors and response format, duplicate identities within one batch, unknown update targets, and update concurrency before finalizing endpoint implementation.
- Define which supplied fields belong to Stone and which to ShelterCase; a single integration record may coordinate both without moving status into Stone.
- History should record actual observed changes, not every repeated receipt. Transport receipt/audit metadata and source-order watermarks may be separate from business history.
- If asynchronous indexing is later added, create indexing intent only for relevant changes and preserve the atomic business-write/task-intent direction of ADR-0004.
- This decision creates no entities, migrations, endpoints, seed records, dependencies, commits or external connections.
