# PY-011 pilot checklist

Issue: https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14. Implementation remains in the original local PY-011 feature worktree. A checked documentation step is not evidence that a parser or retrieval engine works.

## Reviewed local preparation

- [x] Record source units, authoritative field ownership, index filters, exact-query routing, and final PostgreSQL state checks in docs/search/py-011-search-documents.md.
- [x] Prepare local Pydantic evidence models and DocumentKind for stone/profile/event/encyclopedia. These remain uncommitted local feature work; this docs-only branch does not contain them.
- [x] Preserve the profile field walkthrough as a discussion example rather than a finalized engine contract.
- [x] Separate minimal pilot acceptance from later judged datasets and versioning experiments.

## Remaining pilot preparation

- [ ] Generate inspectable operational evidence examples from the prepared source data, retaining external identities and current source filters.
- [ ] Implement the simple encyclopedia parser/export tool and inspect its proposed fourteen documents, including text, source path, section, and type where applicable.
- [ ] Confirm the minimal IDs/revision values needed to instantiate current document models; do not create a general version framework.
- [ ] Review representative exported content and source references, record focused verification evidence, then hand off to index integration.

## Deferred, not blockers

- A reviewed query dataset, expected evidence/candidates, no-result cases, and held-out studies belong to PY-017 after the connected pilot.
- Final query/result contracts, broader chunking strategies, multiple models, and elaborate revision/synchronization rules are later exercises.
- No Typesense, Qdrant, model-provider or Langfuse integration is completed by this ticket's documentation.
