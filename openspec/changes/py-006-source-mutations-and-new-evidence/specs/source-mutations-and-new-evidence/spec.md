## ADDED Requirements

### Requirement: Reviewed mutation contract
Mutation implementation SHALL follow a reviewed domain/input contract specifying source identity, omission/null semantics and current-state ownership before DTOs are introduced.

#### Scenario: Design a later profile update
- **WHEN** the proposed request changes only selected profile fields
- **THEN** the contract makes preservation, clearing and collection replacement behavior explicit

### Requirement: Source-owned lifecycle facts
An accepted update SHALL preserve source ownership of current adoption status and shelter and SHALL NOT infer them from appended event order.

#### Scenario: Append an observation
- **WHEN** a new history observation is accepted
- **THEN** the existing current case status remains unchanged unless an explicitly defined snapshot update accompanies it

### Requirement: Changed evidence experiment
The later exercise SHALL record retrieval before and after an accepted source change and explicit index refresh.

#### Scenario: Add relevant history
- **WHEN** a previously absent observation is persisted and indexed
- **THEN** evaluation can identify the newly retrievable source evidence without silently changing unrelated fixtures
