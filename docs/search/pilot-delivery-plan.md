# Pilot delivery plan and tracker reconciliation

Updated: 2026-11-05. Authority: [project manifesto](../project-manifesto.md), [domain contract](../domain/model.md), and accepted owner decisions. GitHub Issues and the [board](https://github.com/users/PreChatGPTSenior/projects/1/views/1) own delivery status; this document defines scope and dependency boundaries, not a duplicate live status board.

## First result

Produce a meaningful answer over actual stored stones/history and encyclopedia evidence using Typesense lexical retrieval, Qdrant vectors, LangChain, a minimal LangGraph flow, and minimum useful Langfuse tracing. Use prepared consistent inputs. Keep code typed and idiomatic. Do not add production recovery or a full evaluation harness before this path works.

## Ticket slices and dependencies

| Ticket | Pilot slice | Depends on | Later work in the same topic |
| --- | --- | --- | --- |
| [PY-011](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/14) | Concrete evidence models and source-to-document examples/export | PY-010 | Final query/result schemas, elaborate revisions, judged datasets |
| [PY-012](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/15) | Local Typesense and a usable client | PY-011 | Failure/load studies |
| [PY-013](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/16) | Project prepared operational/reference data and explicitly index it | PY-011, PY-012 | Automatic incremental synchronization |
| [PY-014](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/17) | Lexical query, explicit filters, inspectable evidence; exact lookup where needed | PY-013 | Broad query coverage |
| [PY-015](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/18) | One selected embedding model through LangChain | PY-011, PY-013 | Multiple models and extensive version experiments |
| [PY-016](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/19) | Qdrant index and semantic query with the same IDs/filters | PY-015 | ANN/performance comparisons |
| [PY-018](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/21) | Python RRF, stone grouping, authoritative current-state check | PY-014, PY-016 | Judged tuning and fusion alternatives; PY-017 is not a prerequisite |
| [PY-019](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/22) | One selected generation provider and minimum useful Langfuse trace | Ready retrieval; PY-015 for embedding call tracing | Full experiment budgets/accounting, second provider, dashboards |
| [PY-020](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/23) | Fixed LangChain answer with evidence references | PY-018, PY-019 pilot slices | Broad answer-quality evaluation |
| [PY-022](https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/25) | Minimal explicit LangGraph state and retrieval-to-answer path | PY-020 pilot slice | Agent-selected strategies, clarification/follow-ups, checkpoints and comparative studies |

After the first result, PY-017 adds repeatable evaluation and reviewed judgments. PY-021 and PY-023–PY-026 remain later experiments. Deferred parts of PY-019/PY-022 must remain visible as unchecked follow-up work when their pilot slices are delivered; do not close the full topic as though every experiment was completed.

## Encyclopedia pilot proposal

Read stone-rules/stone-encyclopedias/stone-encyclopedia_en.md and split at top-level `##` headings. Retain each chapter's `###` subsections and caveats in its text. The discussed initial configuration is ten whole rock-type chapters plus About This Guide, Rating Scales, Quick Comparison, and General Care Rules: 14 documents. Skip Contents; retain Sources and Editorial Notes in the original source for provenance. This is a pilot proposal to inspect against actual output and the selected embedding model's input limit, not a final chunking contract.

Suggested organization: search/encyclopedia.py contains a pure Markdown-to-search-document function; tools/export_encyclopedia.py reads the source and writes inspectable JSONL. These files are not implemented by this documentation change. No HTTP ingestion endpoint, generic parser framework, or engine integration is required to inspect the output.

## Reconciliation evidence and historical work

- PY-008 and PY-009 design/data work was incorporated into master, including PR #11 (merge 95ee105); the single-record contract and source-owned state supersede earlier batch/replay proposals.
- PY-010 was merged in PR #13 (merge 1d1819d). It includes registration, HTTP scenario coverage, explicit reference seeding, and the per-file loader. Its original history-replay wording is superseded by ADR-0015.
- PY-002 delivered database infrastructure. Real repository wiring and graph rollback arrived later in PY-010; the dedicated two-independent-UoW isolation scenario remains unverified. Do not infer that graph rollback is the same test.
- PY-003 records an earlier flat creation contract. PY-010 replaces that contract; PY-007 replaces its local-database test/check workflow.
- The physical-delete exercise PY-005 is superseded, not implemented. PY-004/PY-006 are deferred and do not gate retrieval. Update contracts must be redesigned before implementing PY-006.
- Historical issue text is retained in collapsed sections with an explicit supersession notice. It is not current implementation guidance.

## Local and remote evidence

At reconciliation, master is 74a4f8a. The PY-011 search models and draft documentation exist only in the original local feature worktree. This documentation branch includes the manifesto and search design drafts so the plan is reviewable, but deliberately does not include application code. It does not claim PY-011 export/indexing is implemented, publish branch links before a push, or authorize a commit, push, merge, paid call, or database mutation.
