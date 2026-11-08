## ADDED Requirements

### Requirement: Connected assistant entrypoint
The entrypoint SHALL execute the configured tool-routed graph and return its grounded answer with usable evidence and trace references.

#### Scenario: Ask for a suitable pet
- **WHEN** a prepared valid request reaches the endpoint
- **THEN** the response is produced by the connected retrieval and answer path, not canned fixture text

### Requirement: Pilot path coverage
Pilot verification SHALL exercise exact PostgreSQL lookup, Typesense-plus-Qdrant hybrid retrieval with final PostgreSQL checks, and both reference source families.

#### Scenario: Review pilot evidence
- **WHEN** the supported demonstration scenarios have run
- **THEN** their outputs and traces identify which real backends and source families participated

### Requirement: Real-model demonstration boundary
The completion record SHALL distinguish deterministic Testcontainers checks from separately invoked live-model observations.

#### Scenario: Confirm pilot completion
- **WHEN** controlled tests and an explicitly configured live demonstration have completed
- **THEN** the record names the model/configuration and observed routes without claiming comprehensive quality evaluation
