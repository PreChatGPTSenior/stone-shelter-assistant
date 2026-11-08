# PY-028: Author the complete fictional type-compatibility JSON guide

## Why

The owner requested a surprise, provider-style reference document for all current rock types. Earlier limited Markdown examples are superseded by ADR-0018: comprehensive fictional pair coverage in JSON.

## What Changes

- Add stone-rules/type-compatibility/stone-type-compatibility_en.json, in English.
- Describe all ten types and every unordered pair, including two pets of the same type.
- Include explicit fictional scope, verdict meanings, stable pair IDs, explanations and cohabitation guidance.

## Capabilities

### New Capabilities
- `type-compatibility-source`: complete citeable fictional pair guidance supplied as JSON.

### Modified Capabilities
None. Operational contracts, models and runtime remain unchanged.

## Impact

Source authoring only. JSON parsing/search projection will be implemented separately in PY-011. Existing encyclopedia Markdown stays unchanged. The separate tarot idea is deferred, not a source dependency.

## Tracking

Local planning ID PY-028; no GitHub issue was created in this change. See [delivery plan](../../../docs/search/pilot-delivery-plan.md) and ADR-0018. Authored locally without a commit.

## Out of scope

Application DTOs, parsers, indexes, embeddings, new rock types, numeric matching engines, tarot and provider calls.
