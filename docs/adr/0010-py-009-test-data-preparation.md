# ADR-0010 PY-009: Separate stone batches and case-event datasets

- Status: Original batch/replay design partially superseded; agreed preparation scope delivered through PY-009/PY-010
- Date: 2026-10-29
- Tracking: [PY-009](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/10)
- Branch: `PY-009-test-data-preparation`
- Related: [PY-008](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/8), [domain model](../domain/model.md), [ADR-0008](0008-external-batch-ingestion-and-partial-updates.md), and [ADR-0009](0009-fictional-pet-stone-profiles.md)
- Refines: The domain model's ingestion design. Creation includes mandatory initial admission history; subsequent life events use a separate dataset and API operation rather than embedding accumulated history in each creation batch.

Update 2026-10-30: [ADR-0013](0013-single-stone-ingestion.md) supersedes the multi-stone batch contract and batch-wide transaction below. The current API registers one stone with its required case, optional profile, and 1 to 100 events containing ADMITTED in any position. Accumulated history may accompany creation. Earlier batch discussion is retained as decision history, not current implementation scope. [ADR-0015](0015-source-owned-adoption-status.md) further supersedes any registration-time status reconstruction below: the source supplies the required current adoptionStatus; imported history is not replayed to determine it.

> Reconciled 2026-11-05: PY-009 preparation was merged through PR #11; PY-010 added the endpoint, loader and ten-scenario dataset in PR #13. ADR-0013/0015 own the current single-stone/source-snapshot contract; ADR-0014 supersedes the earlier Testcontainers-only application restriction below. Later event append and updates remain deferred. Preserve the original batch and transition-driven proposals as history only. See the [current domain contract](../domain/model.md) and [pilot plan](../search/pilot-delivery-plan.md).

## Context

Stone Shelter simulates a fictional world where stones are pets. An existing upstream system registers pets, maintains their profiles and cases, and subsequently reports meetings, observations, care, reservations, adoptions, returns, and transfers.

The owner wants reproducible test data that can grow over time. The learning goal includes observing whether newly received life events become retrievable and appropriately change recommendation evidence. A complete upstream application or UI is unnecessary; JSON fixtures and a future API-calling simulator are sufficient.

This work is tracked separately from defining the domain and ingestion contracts in PY-008. The initial step records decisions only; it does not implement endpoints or generate datasets.

## Decision

Implementation layering is refined by [ADR-0011](0011-dto-to-orm-without-domain-dataclasses.md): map validated DTOs directly to ORM entities, retaining application services and Unit of Work without a separate set of domain dataclasses.

Database iteration follows [ADR-0012](0012-clean-testcontainers-only-development.md): use only clean Testcontainers databases, recreate and reload data as needed, and introduce no legacy-data transfer or backward-compatibility work until the owner explicitly changes that policy.

### Educational happy-path scope

The immediate goal is hands-on learning of Python backend construction, not a production-grade integration platform. The owner writes application code and tests, with explanations and review from the assistant.

The learning scope is:

- Pydantic DTOs with nested objects, collections, enums, and optional profiles.
- SQLAlchemy ORM models, foreign keys, relationships, and one-to-one and one-to-many associations.
- Alembic migrations generated from and checked against the ORM mappings.
- Batch persistence of related stones, cases, and optional profiles through one Unit of Work and a shared transaction.
- Persistence of case events together with their applicable current-state changes in the same transaction.
- Reading the stored data to observe the relationships and resulting case states.

For this increment, assume that incoming data is consistent and noncontradictory: external identifiers are unique, referenced shelters and cases exist when needed, events arrive chronologically, and status transitions obey the agreed lifecycle. These are fixture and upstream assumptions, not extra validation features to implement now.

Keep ordinary Pydantic structure/type validation, database constraints, and rollback on failure. Do not add bespoke transition validation, duplicate/retry handling, timestamp conflict resolution, out-of-order processing, event correction, or recovery orchestration in this increment. Those capabilities can be designed and implemented later.

The loader is only an upstream emulator: read prepared JSON files, send API requests in the agreed order, and report the result. It does not require its own domain model, infrastructure, or resilient ingestion framework.

Verify the increment with a meaningful end-to-end backend happy-path scenario: load the data, read it back, and check relationships, history, and final statuses. Do not expand it into a separate test for every field or implementation step.

### Separate files and API operations

| Dataset | Contents | API direction |
| --- | --- | --- |
| `stones.json` | A creation batch containing stone data, each stone's lifetime case with initial admission events, and an optional profile | Proposed `POST /api/v1/stones/batch`; exact contract pending |
| `case-events.json` | Subsequent life events associated with existing cases by their external UUIDs | A separate event-ingestion operation; multi-case batching details pending |

- Each `shelterCase` includes a required, non-null, nonempty `events` list. At least one event must have `eventType: "ADMITTED"`, recording acceptance into the shelter and the initial AVAILABLE state. Its position in the submitted list is not constrained. A new case must not be created without this accompanying event.
- This initial-event requirement supersedes the earlier blanket exclusion of events from creation payloads. Keep later life history in the separate event operation; do not repeat the initial ADMITTED event in `case-events.json` after it has been created with the case.
- Each StoneBatchItemRequest must contain both `stone: StoneCreateRequest` and `shelter_case: ShelterCaseCreateRequest` (JSON alias `shelterCase`). A stone must not be submitted without its accompanying lifetime case documentation. Both nested objects are required and non-null; only the profile is optional.
- Persist the stone, its accompanying case, the initial events, and the optional profile together within the creation batch transaction. Do not create a case-less stone or an event-less new case through this operation. This settles the earlier open questions about case and initial-history optionality for newly ingested stones.
- A profile may be supplied at creation or added later through partial update. History can continue growing independently of profile changes.
- Files are simulator input. The simulator reads their JSON and calls application APIs; this is not a multipart upload interface or a direct-SQL seed script.
- Use stable external stone, case, and event UUIDs and consistent shelter references across files. The case UUID differs from the stone UUID; its immutable human-readable number is also retained.
- Exact fixture paths and complete JSON envelopes will be agreed before authoring the datasets.

The existing agreed single-case operation is `POST /api/v1/shelter-cases/{external_case_id}/events`. A separate multi-case event batch at `POST /api/v1/shelter-cases/events/batch` was proposed for loading `case-events.json`; this route and its envelope are not finalized by this ADR. Whether to use that batch operation or have the simulator call the single-case operation per case remains open.

### History describes life events

Use the agreed CaseEvent model rather than a technical field-change audit log. Events include admission, transfer, reservation, reservation end, adoption, return, readiness for adoption, adopter meetings, observations, and care events.

Each event carries a source event UUID, occurrence time, type, and description. Applicable events also carry explicit status or shelter transitions. Internal IDs and registration timestamps are assigned by the hub. Duplicate delivery and correction behavior are deferred; the current emulator supplies unique events once.

An event can add evidence without changing current state. Ten adopter meetings are ten events even if the pet remains AVAILABLE. Staff observations do not automatically rewrite the profile.

### Coherent test scenarios

Every test scenario with a final status other than AVAILABLE must include the full event sequence explaining how the pet reached that status. This is an accepted fixture requirement, not an implicit new requirement that every external integration delivery contain its entire past history.

Examples:

- RESERVED: ADMITTED into AVAILABLE, followed by RESERVED with AVAILABLE to RESERVED.
- ADOPTED: ADMITTED into AVAILABLE, followed by direct adoption or a reservation and its completion.
- RETURNED: ADMITTED into AVAILABLE, followed by ADOPTED and then RETURNED with ADOPTED to RETURNED.

The ADMITTED event can establish an initial AVAILABLE state with no previous status. Event order and timestamps must be coherent. Final state must agree with the resulting transition chain once loading is complete.

RETURNED is a distinct current adoption status and is unavailable for new adoption or reservation. It can represent time needed for quarantine, recovery, or assessment. Becoming AVAILABLE again requires a separate readiness transition; the return remains in history afterward. This follows the revised PY-008 domain model rather than the older UNDER_REVIEW vocabulary.

The first representative datasets must include an AVAILABLE pet without a profile and a pet with a profile that reaches RETURNED through the complete transition history. Both cases include ADMITTED in their creation payloads; the second pet's subsequent adoption and return are loaded through the event API.

### Transition-driven loading

The owner selected transition-driven loading:

1. Load `stones.json`, creating stones, optional profiles, cases initially in AVAILABLE, and each case's mandatory initial ADMITTED event.
2. Load `case-events.json`, applying each case's subsequent events in chronological order to reach its intended final state.
3. Start retrieval scenarios after loading is complete and the resulting state agrees with the fixture history.

The creation DTO enforces a nonempty event list containing ADMITTED in any position; it does not enforce array order. The initial event records admission and the initial AVAILABLE state in the same creation transaction. It must not reset an existing case back to AVAILABLE. Subsequent transition events update the case; observations and meetings only add history. Broader chronology, duplicate, and transition validation remains deferred under the happy-path assumptions.

The creation batch is one transaction. Each event request persists its events and applicable state changes in one transaction. The existing single-stone service must not commit independently for each item inside the batch scenario.

The two files are delivered through different API requests, so there is no shared database transaction across them. The emulator sends consistent data in order; partial-batch acceptance, replay of old history, and recovery after interrupted loading are deferred. Snapshot-first loading is not used in this increment.

### Incremental retrieval experiments

After initial loading, append new events through the event API to simulate ordinary shelter life. Later experiments can retain a baseline query result, add evidence, update its search representation, repeat the query, and check whether the evidence is retrieved and used appropriately with event references.

An added event may improve a match, reveal a conflict, or leave the recommendation unchanged. The expectation is appropriate use of new evidence, not a mandatory change in every answer. No embeddings or model-provider calls are introduced by this ADR.

## Consequences

- Stone creation and life-history delivery have separate contracts and can be exercised independently.
- Fixtures remain reproducible through stable identities and explicit lifecycle evidence.
- The simulator and tests must account for ordering and the absence of a cross-request transaction.
- Profiles remain optional; missing traits or care assessments retain the empty/unknown meanings agreed in the domain model.
- Code, migrations, JSON datasets, simulator scripts, and search behavior are not implemented by this documentation change.

## Remaining contract details

- Exact creation and event-batch routes, envelopes, responses, and size limits.
- Fixture locations, shelter reference data, and the simulator interface.

## Deferred hardening

- Source timestamp/version comparisons, late events, and concurrent updates.
- Duplicate conflicts, retries, event corrections, and replay behavior.
- Additional lifecycle and cross-record consistency validation beyond the assumed correct input.
- Partial-batch processing and recovery between requests.

These are future concerns, not prerequisites for the educational happy path or the first selection experiments.
