## ADDED Requirements

### Requirement: Grounded answer and citations
The answer component SHALL return supported claims and references to evidence actually supplied in context.

#### Scenario: Explain a quiet-home recommendation
- **WHEN** the context includes a qualifying candidate, its profile and a reference passage
- **THEN** the answer identifies the actual pet and cites the passages supporting the explanation

### Requirement: Distinct source meanings
Answers SHALL distinguish current operational facts, historical observations, geological reference and fictional compatibility guidance.

#### Scenario: Combine different sources
- **WHEN** a candidate answer uses both an individual observation and a general fictional compatibility rule
- **THEN** the compatibility statement remains labeled fictional guidance and does not redefine current health or availability

### Requirement: Bounded context
Context assembly SHALL use an explicit size budget and preserve source identity and necessary qualifications.

#### Scenario: Assemble several retrieved sections
- **WHEN** selected evidence approaches the model input budget
- **THEN** the context uses a deliberate bounded selection rather than silently truncating the complete concatenated corpus
