# PY-028 authored source design

## Delivered source

stone-rules/type-compatibility/stone-type-compatibility_en.json is an English JSON document presented as an external fictional bureau's guide. Its structure is the source format, not an application DTO or the final search schema. The creative content was delegated to the assistant; no creative approval gate is needed.

## Structure and semantics

- Top-level catalog identity, edition, language, fictional publisher, scope and reading rules.
- Coverage declares all ten exact StoneType values, symmetric unordered pair semantics and 55 entries.
- Ten type portraits provide fictional background without overwriting individual profiles.
- Pair entries contain id, stone_types, verdict, title, explanation, household_agreement, avoid and bureau_note.
- HARMONIOUS, CONDITIONAL and NOT_RECOMMENDED are source vocabulary, not new application enums or numeric scores.
- Both type names are sorted alphabetically for stable pair identity. Same-type pairs describe two distinct pets.
- Rules are symmetric at the pair level. Advice can name different roles without creating a second reverse record.
- Pair conditions and exceptions remain alongside the verdict. Missing individual data stays unknown; care and current eligibility must be checked from operational sources.

## Downstream handoff

PY-011 must inspect and parse this JSON, retain catalog edition and entry ID and render meaningful pair text. It must not use Markdown section splitting on raw JSON, import source type portraits as real profiles, or treat lunar jokes as inputs to a new astronomical subsystem. Source IDs need not be search UUIDs; the preparation layer maps them deliberately.

## Verification

A one-off independent check parsed JSON, extracted StoneType values from its Python declaration and verified all combinations with repetition, ten portraits, unique pair IDs and declared verdicts. No application tests, model calls or database operations were required. Human relevance judgments remain later work.

## Authority

ADR-0018 supersedes the former Markdown/sample-only design and removes the astral catalog prerequisite. The manifesto and domain field ownership continue to apply. No application or test code changed.
