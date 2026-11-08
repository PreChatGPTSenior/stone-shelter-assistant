# Specification and delivery workflow

Updated: 2026-11-08.

## Authority and scope

- The owner's current decisions and [project manifesto](../project-manifesto.md) govern learning priorities and pilot scope.
- [Domain model](../domain/model.md) defines current entities, field ownership, and the registration contract.
- OpenSpec specs describe accepted behavior; their evidence sections distinguish implementation from unverified guarantees. Change artifacts distinguish the current increment from documented future backlog; their existence does not authorize applying them.
- ADRs preserve decisions and supersession history. Requirements retain later experiments separately from the pilot.
- GitHub Issues and the project board own delivery status. Issue descriptions separate current criteria from preserved historical text.
- Generated OpenAPI shows the runtime HTTP schema. It does not replace decisions about field ownership or prove transaction guarantees.

## Current OpenSpec map

| Path | Meaning |
| --- | --- |
| openspec/specs/http-application/spec.md | Implemented HTTP composition/OpenAPI baseline |
| openspec/specs/stone-registration/spec.md | Implemented single-stone graph registration, data loading and database-target boundaries |
| openspec/changes/py-002-db-support | Historical delivered database change; deferred two-UoW verification remains explicit; not archived by this synchronization |
| openspec/changes/py-011-search-documents-and-scenarios | Published models and encyclopedia preparation; remaining operational/new reference evidence for open issue #14 |
| openspec/changes/py-012-typesense-infrastructure | Delivered Typesense connection and verified disposable test support; issue #15 completed |
| docs/search/pilot-delivery-plan.md | Complete linked map of PY-011–PY-030 plus deferred PY-004/PY-006; exact phases/dependencies and remote issue mapping |
| openspec/changes/py-027-pilot-source-corpus, py-028-type-compatibility-source | First source-preparation stage; PY-028 JSON is authored locally; local proposed ticket IDs, not created GitHub issues |
| openspec/changes/py-030-connected-search-pilot | Final connected HTTP/real-model demonstration milestone; local proposed ticket ID |

Every planned ticket in the map has proposal/design/tasks and requirement scenarios. Future implementation remains unchecked. PY-019/PY-022 explicitly separate pilot and post-pilot slices; do not close the complete topic when only the pilot slice is delivered. All work after the pilot remains backlog even though it has OpenSpec artifacts.

The original openspec/README.md describes the initial setup and PY-002-era workflow. Its old In progress statements and unchecked-task wording are historical. README ownership prevents agent edits; use this guide and openspec/config.yaml for the current workflow.

## Working procedure

1. Read the manifesto, domain contract, current dependencies/source, linked issue, and relevant ADRs.
2. Describe the next coherent pilot increment; separate later experiments and avoid duplicate generic contracts.
3. Keep the proposal/design/tasks and GitHub issue aligned when the owner changes scope. Record implementation evidence without marking deferred work complete.
4. Review implementation and run only relevant checks; documentation-only synchronization does not require application tests or model calls.
5. Validate the OpenSpec structure with `openspec validate --all --strict`. This validates artifact structure, not semantic agreement or runtime correctness.
6. Commit/push/merge and archive only when explicitly authorized. Local documents are not published links until pushed.

New current specs may document behavior already merged in prior features without manufacturing retroactive change histories for every ticket. Historical deltas remain available and explicitly labeled; no change is archived here.

ADR-0018 updates the source contract to complete JSON compatibility and supersedes PY-029 as a deferred separate tarot idea. PY-029 artifacts preserve that boundary, not an instruction to create another source.
