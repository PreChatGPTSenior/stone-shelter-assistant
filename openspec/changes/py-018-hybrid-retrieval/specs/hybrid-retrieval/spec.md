## ADDED Requirements

### Requirement: Comparable hybrid branches
Hybrid retrieval SHALL send equivalent hard constraints to both branches and preserve each branch's evidence ranks and score meaning.

#### Scenario: Fuse matching profile evidence
- **WHEN** the same profile appears in both branch result lists
- **THEN** one fused evidence item retains contributions from both ranks

### Requirement: Candidate grouping
Operational evidence SHALL be grouped by stone identity without representing individual events as separate adoption candidates.

#### Scenario: Retrieve several events for one stone
- **WHEN** multiple event documents and a profile refer to the same external stone UUID
- **THEN** the candidate list contains one stone with its supporting evidence

### Requirement: Authoritative eligibility
Actionable recommendations SHALL use PostgreSQL current state for final eligibility and shelter information.

#### Scenario: An indexed candidate is no longer available
- **WHEN** the final PostgreSQL read reports a non-AVAILABLE state
- **THEN** the candidate is not presented as available for adoption; no timestamp-based event replay overrides the database
