## ADDED Requirements

### Requirement: Repeatable evaluation run
The runner SHALL bind results to a versioned dataset, corpus/configuration and per-case predictions so alternative retrieval runs can be compared on the same inputs.

#### Scenario: Compare lexical and hybrid retrieval
- **WHEN** both strategies run on the same reviewed cases and source snapshot
- **THEN** the report contains per-case evidence/candidate results and separate retrieval metrics

### Requirement: Separate quality dimensions
Evaluation SHALL distinguish retrieval relevance, candidate eligibility, tool/argument correctness and free-form answer grounding rather than reducing all behavior to one unexplained score.

#### Scenario: Inspect a fluent but unsupported answer
- **WHEN** an answer lacks supporting retrieved evidence
- **THEN** answer review can flag grounding separately from whether the retrieval stage found relevant candidates

### Requirement: Independent experiment artifacts
Experiment records SHALL remain usable independently of hosted trace retention and SHALL not make paid inference a dependency of ordinary checks.

#### Scenario: Revisit a baseline
- **WHEN** the hosted trace is no longer retained
- **THEN** local dataset/configuration and per-case results remain available for comparison
