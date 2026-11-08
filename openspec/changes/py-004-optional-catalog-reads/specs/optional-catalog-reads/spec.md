## ADDED Requirements

### Requirement: Independent inspection surface
Optional catalog reads SHALL expose current agreed response DTOs without requiring lexical/vector retrieval or changing stored data.

#### Scenario: Inspect a stored stone
- **WHEN** an item lookup is selected for implementation
- **THEN** the response represents the authoritative record without ORM internals or invented historical fields
