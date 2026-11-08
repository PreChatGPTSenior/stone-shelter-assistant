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
- **WHEN** the pilot prepares a selected chapter from the known English Markdown encyclopedia
- **THEN** its nested context remains readable and its section/source reference can be traced to the original file

### Requirement: Distinct reference families
Prepared reference evidence SHALL distinguish encyclopedia and fictional JSON type compatibility with stable family, path and section references. It SHALL preserve pair applicability or other authored conditions without assigning an individual case state.

#### Scenario: Prepare a type-pair compatibility rule
- **WHEN** an authored section describes conditional compatibility between two rock types
- **THEN** its evidence preserves both types, the stated condition and source identity rather than disguising it as a single stone's profile or geological fact

### Requirement: Direct shared evidence handoff
Preparation SHALL supply document objects with shared stable identities directly to lexical/vector adapters; an application JSONL file SHALL NOT be required.

#### Scenario: Prepare the same corpus for both engines
- **WHEN** both adapters consume the prepared evidence
- **THEN** the same logical section or event has the same evidence ID without an intermediate application export file
