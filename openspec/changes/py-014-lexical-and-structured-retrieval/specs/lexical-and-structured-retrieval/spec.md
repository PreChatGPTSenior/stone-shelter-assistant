## ADDED Requirements

### Requirement: Filtered lexical evidence
Lexical retrieval SHALL apply explicit operational constraints and return actual source evidence with ranks and identities.

#### Scenario: Find a small granite for a quiet home
- **WHEN** the query includes granite and small as hard constraints and quiet-home text as a preference
- **THEN** Typesense receives the hard filters and returns inspectable matching evidence rather than unfiltered text-only candidates

### Requirement: Exact lookup without retrieval
Purely structured lookup SHALL use typed PostgreSQL operations without invoking vectorization or lexical search.

#### Scenario: List small granites
- **WHEN** the request requires only exact type and size constraints
- **THEN** matching stored records are obtained from PostgreSQL with deterministic bounded output

### Requirement: Source-specific references
Reference retrieval SHALL retain source family and section references without requiring a stone case.

#### Scenario: Find a type-pair rule
- **WHEN** the selected reference family is the compatibility guide
- **THEN** matching guide passages can be retrieved without adoption status or shelter fields
