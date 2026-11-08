## ADDED Requirements

### Requirement: Actual model tool selection
The pilot graph SHALL use the configured LLM to choose registered tools and produce typed arguments from the request, and SHALL execute the selected application operations.

#### Scenario: Route an exact request
- **WHEN** the model receives a request for small granites with no textual preference
- **THEN** it selects exact lookup and the execution trace shows PostgreSQL retrieval without embedding that exact query

### Requirement: Hybrid and reference tool composition
The graph SHALL support semantic candidate needs and reference questions through distinct typed operations with preserved source identities.

#### Scenario: Explain a candidate and a compatibility rule
- **WHEN** the selected calls include hybrid candidate search and type-compatibility reference search
- **THEN** their results are combined with current-state verification into the shared grounded-answer stage

### Requirement: Bounded execution
The graph SHALL enforce explicit call/round limits and expose executed nodes, tool names, validated arguments and evidence in its trace.

#### Scenario: Complete the first supported request
- **WHEN** the allowed tool calls return evidence
- **THEN** the graph terminates with an answer within its configured bounds rather than entering an open-ended agent loop

### Requirement: Later conversational experiments
Later graph extensions SHALL compare clarification, rewrites, follow-ups and repeated search against the recorded pilot while preserving hard constraints and budgets.

#### Scenario: Evaluate a query rewrite
- **WHEN** rewriting is enabled for a selected dataset run
- **THEN** the rewritten query, extra calls and resulting evidence are recorded separately from the original request
