# ADR-0007 One globally identified shelter case per stone

- Status: Accepted identity design; registration model implemented through PY-010; historical lifecycle/integration details partially superseded
- Date: 2026-10-29
- Supersedes: the AdoptionListing entity choice and open relisting/transfer identity questions in [ADR-0002](0002-stone-and-adoption-listing.md)
- Refines: data ownership and adoption scope in [ADR-0006](0006-rag-and-agent-learning-focus.md)
- Requirements: [Staff hub and case lifecycle](../requirements/rag-learning.md#31-staff-hub-and-lifetime-case-identity)

Integration refinement: [ADR-0008](0008-external-batch-ingestion-and-partial-updates.md) accepts upstream Stone UUIDs, database-backed shelter references, batch creation, partial updates, timestamp/content replay handling, and hub-maintained observed history. Previously open integration details below should be read with that refinement.

> Reconciled 2026-11-05: The lifetime identity decision remains accepted. The domain model and ADR-0015 replace UNDER_REVIEW with RETURNED and require source-owned current state. ADR-0013 replaces batch registration; ADR-0014 permits persistent local application data. Original transition/integration discussion below is decision history, not a second current contract. See the [current domain contract](../domain/model.md) and [pilot plan](../search/pilot-delivery-plan.md).

## Context

The application is a central information hub for multiple shelters, initially two. A visitor describes adoption preferences to a staff member at a separate assistance point; the staff member uses the assistant to find and explain suitable stones. The chatbot is a staff tool, not a direct public user interface.

An external service sends JSON to our ingestion API with specimen, shelter and adoption-accounting data. We simulate that external caller using JSON fixtures and a sending script, rather than inserting directly into the database. The full upstream system and synchronization UI are not being built.

The owner considered a separate case per shelter, then chose one case for the stone's entire history across the network. A simulated external numbering/identity service assigns the case identity and display number.

## Decision

### Entities and ownership

- `Stone` represents the physical specimen and its properties, retaining its own UUID. Adoption status does not belong to Stone.
- `Shelter` represents a shelter with an identity, name and address. Start with two shelters. Coordinates, distance ranking and geographic search are not required now.
- `ShelterCase` represents the stone's lifetime adoption/accounting case, including its current status, current assigned shelter and history. It replaces the previously proposed AdoptionListing; do not add both as duplicate current-state entities.
- A Stone has at most one lifetime ShelterCase in this network; every case references exactly one Stone. Existing catalog-only records can precede case ingestion; whether the importer requires a case in every incoming record remains open.
- One Shelter is associated with many cases; each case has one current assigned shelter. Historical placements belong in the case history.

### Identity

The external identity service assigns an immutable, globally unique **case UUID**, which our application preserves across imports and transfers. This UUID identifies the case across systems; it is distinct from the Stone UUID. Do not generate a replacement case UUID on each received message.

The service also supplies an immutable, unique, human-readable **case number**, such as `0001-2026-P1`. The example encodes a sequence, year and issuing subdivision. We know this upstream convention but treat the supplied number as a string: preserve leading zeroes and do not reconstruct it or derive database relationships from it.

Case UUID is the canonical integration identity. Case number is a unique business lookup key for staff search. Both must remain unique and consistent; the same number paired with a different case UUID is an identity conflict, not a second case to insert silently. Exact validation and conflict response contracts are still to be designed.

If an issuer code remains embedded in a number after transfer, it refers to the original issuing subdivision, not the current shelter. Search by number must continue to find the case after a move. Whether lookup supports exact, prefix or normalized matching is open.

### Returns and transfers

- Reservation and adoption activity update the existing case and its history.
- A return continues the same case, preserving both its UUID and case number. Repeated adoption/return cycles do not create replacement cases.
- A transfer between shelters also continues the same case. Update the current shelter and record origin, destination and time in history; preserve case UUID, case number and Stone identity.
- No transfer closes one case and opens another merely because the shelter changed.
- The assigned shelter is an accounting/custody association. An adopted stone must not be presented as physically available for pickup there solely because the association is populated.

### Current state, history, and assistant behavior

Persist current case state and explicit history sufficient for staff to inspect relevant adoption and movement events. This does not require event sourcing. The accepted statuses and business transitions are defined below; history payloads and atomic state/history update mechanics remain to be designed.

### Accepted case statuses

| Status | Meaning |
| --- | --- |
| `UNDER_REVIEW` | The case is recorded, but the stone is not currently eligible for adoption recommendations pending review |
| `AVAILABLE` | The stone is eligible for adoption and recommendation |
| `RESERVED` | The stone is reserved and is not available for a new adoption selection |
| `ADOPTED` | The stone has been adopted and is not available for selection; the lifetime case is retained |

### Accepted business transitions

| From | To | Business event |
| --- | --- | --- |
| `UNDER_REVIEW` | `AVAILABLE` | Review completed and the stone released for adoption |
| `AVAILABLE` | `RESERVED` | Reservation created |
| `RESERVED` | `AVAILABLE` | Reservation cancelled or expired |
| `RESERVED` | `ADOPTED` | Adoption completed against a reservation |
| `AVAILABLE` | `ADOPTED` | Adoption completed directly; prior reservation is not required |
| `ADOPTED` | `UNDER_REVIEW` | Stone returned; review is required before availability |

A return must not make a stone immediately available: use `ADOPTED -> UNDER_REVIEW`, followed by a separate review-completion transition. `RETURNED` is a history event, not an additional current status. `ADOPTED` is not terminal for the lifetime case because a return may reopen availability after review. Every transition preserves case UUID, case number and Stone identity.

Transfers remain movement/history operations rather than an additional current status. They preserve the case identity and change the current shelter. Which statuses permit transfer, whether an active reservation blocks transfer, and whether the receiving shelter requires review remain open; the earlier suggestion to allow transfers only from AVAILABLE or UNDER_REVIEW is not adopted as a rule here. The initial state on first ingestion and reservation expiry timing also remain open.

The assistant combines specimen properties, encyclopedia evidence, current availability, relevant history and shelter address. Availability and current shelter are read from authoritative database state rather than trusted from a potentially stale embedding. Initial assistant capabilities remain read/recommendation tools; adopting, reserving or transferring through the chatbot requires a separate explicit decision.

The external ingestion contract is distinct from the existing `StoneCreateRequest`. The latter currently ignores undeclared adoption fields. The future integration API may legitimately accept authoritative case state; define its validation, ordering and duplicate behavior explicitly instead of globally ignoring that state.

## Consequences

- The earlier rule "transfer creates a new case" is superseded. A return and a transfer both preserve lifetime case identity.
- Adoption lifecycle data is now part of the planned domain for staff selection, not excluded wholesale as it was in the earlier CRUD/RAG direction. Status implementation remains future work.
- No user-facing manual-entry UI, geolocation system, external identity service, authentication system, or database schema is implemented by this decision.
- Ingestion requires enough stable identity to link subsequent messages to the same specimen and case. The source's Stone identity mapping, event ordering/versioning, snapshot-versus-delta behavior, batch atomicity and malformed-record handling remain open.
- Enforce unique case UUID, case number and the one-case-per-Stone relationship when persistence is implemented. Never merge stones or cases by name, biography, display-number parsing or embedding similarity.
