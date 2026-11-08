# PY-023: Add durable indexing intent and measured freshness recovery

## Why

Indexes are not implemented; no outbox/worker exists. ADR-0004 selects PostgreSQL-backed durable tasks rather than Kafka.

## What Changes

- Persist business changes and indexing intent in one PostgreSQL transaction.
- Deliver updates to both indexes outside that transaction and study bounded recovery/freshness.

## Capabilities

### New Capabilities
- `durable-indexing-and-freshness`: Add durable indexing intent and measured freshness recovery.

### Modified Capabilities
None in this planning change. Existing implementation is not changed by these artifacts.

## Impact

Phase: After the connected pilot. Dependencies: PY-018/PY-017; PY-006 only for mutation-specific scenarios.

Follow docs/project-manifesto.md, docs/domain/model.md, ADR-0015, ADR-0016 and ADR-0017. This is a learning project: narrow happy-path pilot first, idiomatic typed code, then measured experiments. This document authorizes no implementation or provider spending.

## Tracking

https://github.com/PreChatGPTSenior/stone-shelter-lab-py/issues/26

The local [delivery plan](../../../docs/search/pilot-delivery-plan.md) maps this change to sequencing and GitHub tracking. Planned work stays unchecked until verified; a completed pilot slice does not complete later experiments.

## Out of scope

No Kafka, distributed transaction or production HA. Do not implement before the pilot.
