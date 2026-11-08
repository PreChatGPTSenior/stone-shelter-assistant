## ADDED Requirements

### Requirement: Traceable lexical indexing
The indexer SHALL write prepared operational and reference evidence with stable IDs, source references and applicable filter fields while preserving distinct source families.

#### Scenario: Index a profile and a compatibility section
- **WHEN** both prepared documents are submitted to the lexical index
- **THEN** each can be read back with its own provenance and only the profile carries individual case-status/shelter metadata

### Requirement: Repeatable indexing
Repeated indexing of unchanged prepared evidence SHALL reuse document IDs without increasing the unique-document count.

#### Scenario: Index the same corpus twice
- **WHEN** the explicit command upserts an unchanged corpus twice into a disposable index
- **THEN** the second run leaves one stored document per shared evidence ID
