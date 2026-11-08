## ADDED Requirements

### Requirement: Traceable pilot invocation
A pilot invocation SHALL link graph/tool/retrieval/model stages to one trace with evidence identities, model configuration, latency and available token/cost data.

#### Scenario: Inspect a recommendation trace
- **WHEN** a configured model answers using retrieved evidence
- **THEN** the owner can inspect executed tool names, arguments, sources and answer, with credentials excluded

### Requirement: Explicit live execution
Live model calls SHALL be explicitly invoked outside make check with selected model and finite call/output limits.

#### Scenario: Run normal automated checks
- **WHEN** the check suite executes
- **THEN** it requires no provider credentials or paid inference

### Requirement: Later experiment budgets
The post-pilot runner SHALL account for all model stages, keep judge budgets separate, label estimated versus reported usage and enforce local limits before scheduling further calls.

#### Scenario: Reach an experiment budget
- **WHEN** a further call would exceed the configured available allowance
- **THEN** the runner schedules no further call and records a budget stop rather than a successful zero-cost result
