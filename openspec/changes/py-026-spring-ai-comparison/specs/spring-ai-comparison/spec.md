## ADDED Requirements

### Requirement: Shared evaluation basis
The Java comparison SHALL use the same reviewed inputs and behavioral constraints as the Python baseline, with explicit differences.

#### Scenario: Compare a recommendation
- **WHEN** both implementations process the same case and configuration where supported
- **THEN** candidate/evidence IDs, grounding, latency and cost can be compared

### Requirement: Observable framework comparison
The report SHALL compare fixed RAG and selected tool-routed behavior without requiring identical internal orchestration.

#### Scenario: Inspect framework results
- **WHEN** the graph or tool plumbing differs
- **THEN** the report separates implementation effort and framework differences from answer/retrieval quality
