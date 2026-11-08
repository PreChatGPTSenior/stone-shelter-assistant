## ADDED Requirements

### Requirement: Complete fictional JSON source
The guide SHALL be an English JSON document explicitly labeled as fictional pet-world guidance. It SHALL describe every current StoneType and every unordered type pairing including two distinct pets of the same type.

#### Scenario: Inspect complete pair coverage
- **WHEN** the catalog is checked against the ten current StoneType values
- **THEN** it contains exactly 55 distinct unordered pairs: 45 mixed-type pairs and ten same-type pairs, with no extra type names

### Requirement: Symmetric citeable entries
Every pair SHALL have a unique stable source ID, both type names, a declared categorical verdict, a meaningful explanation and cohabitation guidance. The source SHALL explicitly state that reversed type order selects the same entry.

#### Scenario: Reverse a pair lookup
- **WHEN** a reader looks up the same two types in reverse order
- **THEN** the same pair entry and verdict apply, with any role-specific advice preserved in its prose

### Requirement: Fictional guidance remains distinct from individual facts
The source SHALL distinguish general fictional pair advice from individual observations and current case eligibility. Planetary jokes SHALL NOT require another source or service.

#### Scenario: Read advice about an unavailable pet
- **WHEN** a harmonious general pairing includes an individual whose case is not AVAILABLE
- **THEN** the source supplies no permission to adopt that pet and does not override PostgreSQL current state

### Requirement: Explicit unsupported coverage
Types not included in this edition SHALL remain unspecified rather than receive an invented compatibility rule.

#### Scenario: Request an unsupported type
- **WHEN** a type outside the current ten appears in a future request
- **THEN** this source provides no matching rule or default positive verdict
