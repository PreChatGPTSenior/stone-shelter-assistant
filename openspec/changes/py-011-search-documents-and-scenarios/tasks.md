# PY-011 preparation checklist

Issue: https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14. Published in PR #32. Before merge, OpenSpec validation passed and 43 tests passed, including the encyclopedia preparation scenario. The remaining projection work is unverified.

## Existing local work

- [x] Define Pydantic evidence models and DocumentKind for stone, profile, case event and encyclopedia; local implementation, not a completed index integration.
- [x] Implement fourteen-section encyclopedia preparation and its real-source scenario; preserve source path, headings and current UUIDv5/hash conventions.
- [x] Document current index filters, exact SQL routing and final PostgreSQL state authority.

## Remaining work after source authoring

- [ ] Load stored graphs explicitly and prepare stone, optional profile and individual event documents.
- [ ] Preserve external parent/event IDs and current source-owned status/shelter without replay.
- [ ] Add a reference kind/model and JSON preparation for PY-028 compatibility entries, preserving both types, source edition, pair IDs and guidance.
- [ ] Record source-key/rendered-text/hash conventions and inspect representative output from every source family.
- [ ] Verify a meaningful graph-to-evidence scenario using Testcontainers and focused reference-source scenarios.
- [ ] Hand document objects directly to index integration; record verification without creating application JSONL storage.

Reviewed relevance labels and comprehensive evaluation belong to PY-017 after the connected pilot. Do not mark the new reference preparation complete just because these planning artifacts exist.
