## ADDED Requirements

### Requirement: Semantic source identity
Qdrant SHALL store externally generated vectors with the same evidence IDs and source references used by Typesense.

#### Scenario: Retrieve a known profile semantically
- **WHEN** a query vector searches the prepared profile corpus
- **THEN** the result resolves to the same profile evidence ID and parent stone as lexical retrieval

### Requirement: Semantic hard filters
Semantic retrieval SHALL apply the same logical hard filters as the lexical branch before returning candidates.

#### Scenario: Search available stones in one shelter
- **WHEN** the semantic request specifies AVAILABLE and a shelter UUID
- **THEN** returned operational evidence satisfies both indexed constraints

### Requirement: Isolated engine verification
Automated Qdrant integration tests SHALL use disposable containers and explicit settings, without local development volumes or provider calls.

#### Scenario: Run a vector adapter test
- **WHEN** the test indexes controlled vectors
- **THEN** queries and cleanup target only its disposable Qdrant instance
