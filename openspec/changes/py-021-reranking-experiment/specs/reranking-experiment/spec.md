## ADDED Requirements

### Requirement: Controlled reranking comparison
The experiment SHALL compare the same candidate/evidence set before and after reranking, preserving provenance and reporting ranking change, latency and usage.

#### Scenario: Enable the reranker
- **WHEN** a frozen hybrid candidate set is ranked again
- **THEN** the result records both original and reranked order without attributing embedding or corpus changes to the reranker

### Requirement: Bounded reranking input
Reranking SHALL use explicit candidate and input-size limits.

#### Scenario: Rerank long source passages
- **WHEN** selected passages approach the model limit
- **THEN** the documented input policy is applied and recorded rather than silently changing the evidence
