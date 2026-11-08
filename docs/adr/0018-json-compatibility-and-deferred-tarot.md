# ADR-0018 Author complete fictional compatibility as JSON; defer the separate tarot idea

- Status: Accepted owner decision; compatibility source authored locally, ingestion not implemented
- Date: 2026-11-08
- Supersedes: ADR-0017's Markdown compatibility format, limited pair sample and immediate astral-catalog prerequisite

## Decision

The owner delegated the creative content and requested a surprise reference source, as if an external provider had delivered it. Use every current StoneType and cover every possible pair in an English JSON document. The material is intentionally fictional: emotions, imagined physiology, domestic habits and absurd planetary jokes may coexist. It is not biological or geological evidence.

The source is stone-rules/type-compatibility/stone-type-compatibility_en.json. It contains ten fictional type portraits and 55 unordered, symmetric pair entries: 45 distinct-type combinations and ten combinations of two different pets of the same type. Reversing a pair selects the same entry; prose may still describe each member's different needs.

Each pair has a stable textual ID, both type names, categorical verdict, explanation, household agreement, things to avoid and an anecdote from a fictional bureau. The catalog itself explains verdicts, coverage, fictionality and citation rules. No numeric score or probabilistic claim is introduced. Types outside this edition remain unknown.

The guide supplies general fictional guidance. Individual profiles, observed history and care needs must be checked independently; missing personal data is not a favorable assessment. Current adoption availability and shelter remain PostgreSQL facts. A NOT_RECOMMENDED pairing's brief-visit advice does not authorize routine cohabitation.

## Tarot boundary

The owner reframed the astral idea as a separate future tarot-card divination program. Do not create its source, cards, program, endpoint, tool, model fields or integrations now. The previously proposed PY-029 source task is superseded and deferred as a historical placeholder; it is not a dependency of corpus preparation, indexing, routing, pilot acceptance or the tutorial. A new scope must be agreed if that separate project is resumed.

A planetary joke within the compatibility JSON is part of that authored source; it does not create a requirement for an astral catalog, real astrology or a tarot service.

## Downstream learning work

The pilot has two reference families: the existing Markdown encyclopedia and the JSON compatibility guide, plus operational data. PY-011 will parse the provider-style JSON and deliberately render pair evidence with both types, entry ID, source path and edition. Do not pass JSON through MarkdownHeaderTextSplitter or force a pair into a single stone_type field. No parser, DTO, ORM, indexing or search code changes are authorized by source authoring.

## Verification

The JSON was parsed successfully and its type vocabulary checked against the StoneType declaration without importing the application. All 55 combinations with repetition are present exactly once, IDs are unique and verdicts use the declared catalog vocabulary. This is a one-off source integrity check, not a new application test suite or a claim of retrieval quality. OpenSpec structure is validated separately. No Git commit or remote ticket update is implied.
