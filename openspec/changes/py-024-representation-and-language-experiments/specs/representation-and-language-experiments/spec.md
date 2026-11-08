## ADDED Requirements

### Requirement: Controlled representation comparison
Each comparison SHALL identify the changed representation/model factor and hold other inputs constant or explicitly report unavoidable differences.

#### Scenario: Compare encyclopedia chunk sizes
- **WHEN** two chunking strategies run on the same source version and question set
- **THEN** the report separates evidence recall, candidate quality and context/latency effects

### Requirement: Language evidence
Multilingual experiments SHALL retain original query language and source language with per-case retrieval and answer observations.

#### Scenario: Search English evidence with Russian wording
- **WHEN** the configured model processes a Russian preference query
- **THEN** the report records retrieved source IDs and grounded answer behavior rather than assuming cross-language equivalence
