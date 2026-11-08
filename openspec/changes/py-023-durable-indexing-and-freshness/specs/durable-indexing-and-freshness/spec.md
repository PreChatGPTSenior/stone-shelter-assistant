## ADDED Requirements

### Requirement: Atomic indexing intent
A supported business write and its indexing intent SHALL commit together in PostgreSQL, while model and search-engine calls SHALL run outside that transaction.

#### Scenario: Commit a registration for indexing
- **WHEN** the business transaction succeeds
- **THEN** a durable pending intent exists for the committed source graph

### Requirement: Independent delivery recovery
The worker SHALL retain per-engine progress and allow bounded retry without duplicating logical documents or overwriting newer evidence with stale work.

#### Scenario: One index update fails
- **WHEN** the other engine has accepted the same source revision
- **THEN** pending delivery remains observable and can be retried without pretending a distributed atomic commit occurred

### Requirement: Freshness observation
Experiments SHALL distinguish stale indexed eligibility, final PostgreSQL rejection and retrieval misses caused by stale filters.

#### Scenario: Refresh a case status
- **WHEN** the source state changes and indexes are refreshed
- **THEN** the experiment records before/after candidate visibility and the final authoritative check
