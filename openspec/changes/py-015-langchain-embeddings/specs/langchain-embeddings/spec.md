## ADDED Requirements

### Requirement: Compatible vectors
Document and query embeddings SHALL use the same selected embedding space with recorded configuration and dimensions.

#### Scenario: Embed a question for an indexed corpus
- **WHEN** the document and query embedding paths run with the selected configuration
- **THEN** the query vector is compatible with stored vectors and the configuration can be identified

### Requirement: Visible embedding input
Embedding preparation SHALL preserve the exact input text and verify it fits the selected model input policy.

#### Scenario: Prepare an encyclopedia chapter
- **WHEN** a selected chapter is ready to embed
- **THEN** its full intended text is either within the model limit or explicitly split with preserved provenance rather than silently truncated
