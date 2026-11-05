## ADDED Requirements

### Requirement: Traceable pilot evidence
Evidence preparation SHALL preserve source text/facts and sufficient identity to resolve and cite the originating stone, profile, event, or encyclopedia section. Missing profiles SHALL NOT produce invented profile facts.

#### Scenario: Prepare a stone with a profile and history
- **WHEN** a prepared consistent stone has a profile and case events
- **THEN** preparation yields separate stone, profile, and event evidence with shared parent references rather than a fabricated summary of the complete history

### Requirement: Source-owned operational filters
Operational documents SHALL copy current type, size, adoption status, and shelter from the authoritative source snapshot. Historical event type or order SHALL NOT calculate current state. Reference sections SHALL NOT carry an individual's adoption status, size, or shelter.

#### Scenario: Prepare historical evidence for a returned pet
- **WHEN** a RETURNED case includes a historical ADOPTED event
- **THEN** the event document retains its historical type while its current-state filter metadata remains RETURNED

### Requirement: Inspectable encyclopedia output
The pilot preparation SHALL retain meaningful encyclopedia text and caveats with source path and section identity. It SHALL support inspecting generated documents before engine integration, without requiring a generic parser framework or a complete evaluation dataset.

#### Scenario: Prepare a rock-type chapter
- **WHEN** the pilot exports a selected chapter from the known English Markdown encyclopedia
- **THEN** its nested context remains readable and its section/source reference can be traced to the original file
