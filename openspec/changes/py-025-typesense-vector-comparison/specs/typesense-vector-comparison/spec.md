## ADDED Requirements

### Requirement: Comparable backend inputs
The comparison SHALL reuse the same vectors and source identities and disclose filter/metric/search-mode differences.

#### Scenario: Compare vector-only results
- **WHEN** both engines query the same vectors with equivalent filters
- **THEN** observed differences are reported with exact/ANN configuration and tie handling

### Requirement: Separate fusion comparison
Built-in hybrid comparisons SHALL record the fusion algorithms and distinguish their effect from vector storage.

#### Scenario: Compare Typesense hybrid and Python RRF
- **WHEN** the same query/corpus is run through both paths
- **THEN** quality and latency reports identify the differing fusion settings rather than claim an unexplained engine advantage
