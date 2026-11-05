# PY-011: Prepare pilot search evidence

## Why

Registration and prepared source data already exist, but neither index can be populated until operational records and encyclopedia text have concrete search representations. Obtain inspectable evidence documents first, following the happy-path manifesto rather than designing a complete research harness.

## What Changes

- Describe and review the minimal source-to-document mapping for stone, optional profile, case event, and encyclopedia chapter/section.
- Reuse the local Pydantic search models and document kinds; preserve source identity, text, citations, and current-state filter metadata.
- Prepare a simple Markdown parser/export path and enough concrete operational examples to inspect before index adapters.
- Separate later dataset, schema-evolution, and representation experiments from pilot acceptance.

## Capabilities

### New Capabilities
- `search-evidence-preparation`: inspectable derived evidence for the initial lexical and vector adapters.

### Modified Capabilities
None. Registration, authoritative operational entities, and their HTTP contract remain unchanged.

## Impact

Planned work in search/ and an explicit export tool, plus documentation. Pydantic models and example docs exist in the original local PY-011 feature worktree, not in master and not as working retrieval. This docs-only branch adds no application code.

## Scope Boundary

No engine integration, provider calls, generic storage framework, final query/result schemas, exhaustive judged dataset, negative-path matrix, automatic synchronization, or elaborate versioning. Existing model revision fields are not an excuse to build a version service before exporting a document.

## Tracking

- Issue: https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14
- Feature branch: PY-011-search-documents-and-scenarios (local)
- Documentation reconciliation branch: docs/sync-spec-and-pilot-plan (local)
- Plan: docs/search/pilot-delivery-plan.md; priorities: docs/project-manifesto.md
