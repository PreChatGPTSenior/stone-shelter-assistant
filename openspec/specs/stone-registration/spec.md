# Single-stone registration

## Purpose

Describe the graph-registration behavior merged through PY-010, the source-owned case state, and the supported data-loading path. The [domain model](../../../docs/domain/model.md) owns exact fields, aliases, enums, and nullability. ADR-0013, ADR-0014, and ADR-0015 supersede batch ingestion, test-only application persistence, and status replay respectively.

## Requirements

### Requirement: Single-record registration contract
The API SHALL accept POST /api/v1/stones with one required stone, one required shelterCase, and an optional profile. It SHALL require the case's source-provided adoptionStatus, currentShelterId, admissionDate, identity, case number, and event collection. It SHALL NOT accept a multi-stone batch as its registration contract.

#### Scenario: Register a pet without a profile
- **WHEN** a valid request contains a stone and its complete accompanying case but no profile
- **THEN** registration returns HTTP 201 with exactly an id field containing the generated internal stone UUID and creates no profile row

#### Scenario: Register a pet with a profile
- **WHEN** a valid request includes profile facts
- **THEN** those facts are persisted as the related profile and omitted socialization traits become an empty set without inventing unknown care or health values

### Requirement: Source-owned current state
Registration SHALL preserve supplied current adoption status and current shelter without calculating them from historical event types, timestamps, array order, or case-number suffix. Allowed current states SHALL be AVAILABLE, RESERVED, ADOPTED, and RETURNED.

#### Scenario: Register an accumulated history
- **WHEN** a coherent request supplies a RETURNED current state and an event collection that includes ADMITTED and later life events
- **THEN** registration stores RETURNED as supplied, retaining event facts without replaying state changes

### Requirement: Accompanying admission history
Registration SHALL require a nonempty events collection containing ADMITTED in any position. The collection SHALL contain at most 100 events. Existing custom validation codes SHALL remain distinct from generic structural validation errors.

#### Scenario: Admission is not the first array item
- **WHEN** an otherwise valid request contains ADMITTED after another event in array order
- **THEN** the request is not rejected merely because ADMITTED is not first

#### Scenario: Event count exceeds the accepted limit
- **WHEN** a request supplies more than 100 events
- **THEN** HTTP 422 detail contains CASE_EVENT_LIMIT_EXCEEDED with limit and actual context

#### Scenario: Nonempty history lacks admission
- **WHEN** a nonempty event collection lacks ADMITTED
- **THEN** HTTP 422 detail contains CASE_ADMITTED_EVENT_REQUIRED with required_event_type context

### Requirement: Atomic ORM graph persistence
The application service SHALL construct ORM entities directly from validated input and persist stone, required case, optional profile, and events in one session with one explicit UoW commit. Repositories SHALL NOT commit independently. Failed persistence SHALL NOT leave a partially registered graph.

#### Scenario: Successful graph commit
- **WHEN** registration commits successfully
- **THEN** an independent database session can read the linked records and supplied source facts

#### Scenario: Database failure while saving the graph
- **WHEN** a database constraint prevents registration from committing
- **THEN** no records from that failed graph remain persisted and previously committed records remain intact

### Requirement: Deliberate application and test database targets
The locally running application SHALL be allowed to use persistent Compose PostgreSQL. Database-backed automated tests and migration verification SHALL use disposable Testcontainers with explicit connection settings rather than the persistent application database.

#### Scenario: Database-backed scenario execution
- **WHEN** the integration suite starts
- **THEN** its fixtures apply the migration chain to a disposable container and provide that explicit target to the application and verification sessions without .env fallback

### Requirement: File-based source emulator
The emulator SHALL submit fixtures/stones/<stone.externalId>.json files as separate HTTP registration requests. Reference shelter seeding SHALL remain a separate explicit operation. The loader SHALL NOT silently retry or skip duplicate registrations.

#### Scenario: Load prepared records
- **WHEN** the two reference shelters exist and the loader submits valid stone files to the endpoint
- **THEN** each successful HTTP 201 is reported and its complete graph is committed independently of other files

## Evidence and exclusions

PY-009 supplied ORM/DTO/fixture preparation in PR #11 (merge 95ee105); PY-010 service, endpoint, loader, and scenario coverage were merged in PR #13 (merge 1d1819d). Recorded PY-010 make check result: 41 passed. This synchronization reviewed source/test wiring; it did not rerun that suite. Atomic persistence failures are covered at service level; do not claim a custom HTTP mapping for database exceptions.

Later event append, partial updates, transition validation, replay idempotency, source ordering, automatic index refresh, a custom HTTP error envelope, and full CRUD remain outside implemented scope. The original flat PY-003 request is historical and is not a second supported registration contract.
