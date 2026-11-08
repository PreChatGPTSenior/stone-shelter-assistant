# ADR-0009 Fictional pet-stone profiles and authored compatibility rules

- Status: Profile registration implemented through PY-010; authored compatibility remains planned
- Date: 2026-10-29
- Refines: [ADR-0006](0006-rag-and-agent-learning-focus.md) and [ADR-0008](0008-external-batch-ingestion-and-partial-updates.md)
- Requirements: [Fictional pet profiles](../requirements/rag-learning.md#4-fictional-pet-profiles-and-compatibility)

> Reconciled 2026-11-05: The exact profile enum vocabulary, nullability and storage are implemented and documented in docs/domain/model.md. The earlier open vocabulary discussion below is historical. Type-compatibility and astral source content remain unimplemented future exercises; neither blocks the pilot. See the [current domain contract](../domain/model.md) and [pilot plan](../search/pilot-delivery-plan.md).

## Context

Stone Shelter is intentionally set in a fictional world where stones are pets. The goal is an engaging domain for learning ingestion, retrieval, tool use, agent workflows and evaluation, not a scientifically realistic system for maintaining geological specimens. Staff describe individual pet-stones and help find suitable future families.

The imported geological encyclopedia remains a useful source, but it is not the authority for fictional personalities, health, trauma, wishes or compatibility rules. Those are authored world data. They do not require scientific justification in order to exist in the domain.

## Decision

### Individual Stone profile

Accept the following additional conceptual fields on the individual Stone profile. They remain separate from ShelterCase status, current shelter and adoption history. A transfer or return does not erase the profile.

| Conceptual field | Representation | Meaning |
| --- | --- | --- |
| Socialization traits | A set of enum values, assigned by staff | Multiple concurrent social preferences or characteristics |
| Care level | Enum/category | The amount of care and attention the pet-stone needs |
| Health description | Free text | Fictional health observations, chronic conditions and care notes |
| Trigger/experience description | Free text | Past experiences, fears, sensitivities and triggers recorded by staff |
| Preferred environment | Free text | The stone's wishes about its future family and surroundings |

Socialization is not a single mutually exclusive label or an ordinal "socialization score". A stone may prefer living without other stones while enjoying children. Proposed vocabulary discussed includes PREFERS_SOLITUDE, ENJOYS_OTHER_STONES, GOOD_WITH_CHILDREN and NEEDS_SLOW_INTRODUCTION; exact names and valid combinations remain to be finalized before implementation.

Care intensity and chronic conditions are different dimensions. A chronic fictional condition may require little additional effort. Represent the amount of care with the category and the condition with text rather than equating "chronic" with a high-intensity level. STANDARD, ADDITIONAL and INTENSIVE are a proposed vocabulary, not an implemented enum or a finalized API contract.

Illustrative fictional notes might describe fear of running water after living in an aquarium, or a wish for a quiet family, a soft cushion and evening readings. Such examples illustrate field purpose; they are not records to insert automatically.

### Compatibility knowledge

Create a separate authored Markdown document for compatibility between rock types. Its rules are explicitly fictional game/world rules, not claims about real geology. The owner will author the document later; this ADR does not invent a compatibility matrix.

Keep this compatibility source distinct from the geological encyclopedia, with clear source identity and fictional labeling for later ingestion and explanations. How compatibility exceptions, directionality and precedence over individual observations are resolved remains open.

### Retrieval and explanations

Use staff-authored enum values for precise filtering when needed, and textual profile descriptions as future retrieval/embedding material. Compatibility rules form another knowledge source for RAG. Search design itself remains postponed until entity definitions and basic population are established.

Ground fictional-domain explanations in actual profile records and authored world rules. Do not invent a pet's diagnosis, trauma, preferences or compatibility just because it would fit the story. Fictional truth is valid domain evidence; distinguish it from geological facts when the distinction is relevant.

Missing data means unknown, not no triggers, healthy, compatible with every type or suitable for all families. Exact nullable/default/clearing behavior is part of the future ingestion contract and is not finalized here.

## Consequences

- All future domain discussions must preserve the framing: stones are pets in a fictional world. Do not reject agreed gameplay properties merely because real rocks do not have those properties.
- Keep specimen identity/profile, lifetime case/accounting state, and shared compatibility knowledge as separate responsibilities.
- These profile fields are conceptual and accepted; exact field names, enum vocabulary, text limits, persistence mapping and update semantics remain implementation-time decisions.
- No human or animal medical model, real-world diagnostic claims, clinical workflow, or scientific compatibility guarantee is implied.
- This documentation does not create tables, migrations, profile data, compatibility rules, endpoints, embeddings or tools.
