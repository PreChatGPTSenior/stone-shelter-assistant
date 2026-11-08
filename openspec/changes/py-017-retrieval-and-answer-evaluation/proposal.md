# PY-017: Establish the baseline and incremental evaluation harness

## Why

No evaluation runner or chosen evaluation framework exists. Source examples and existing tests are not relevance judgments.

## What Changes

- Capture a small reviewed dataset and the first working baseline.
- Measure retrieval, candidate selection, tool behavior and answer grounding separately.
- Select an evaluation framework when implementing and preserve local reproducible artifacts.

## Capabilities

### New Capabilities
- `retrieval-and-answer-evaluation`: Establish the baseline and incremental evaluation harness.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-030; retrieval and trace outputs; PY-019 budgets for live runs.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/20

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No framework installation or live evaluation in this docs-only change. Comprehensive datasets and judges do not block PY-030.
