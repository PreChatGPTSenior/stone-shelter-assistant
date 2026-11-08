# PY-023 tasks

Phase: After the connected pilot. Dependencies: PY-018/PY-017; PY-006 only for mutation-specific scenarios.

All items below are planned, not implemented by this documentation change.

- [ ] 1. Design the minimal durable task schema and source graph revision policy.
- [ ] 2. Write indexing intent in supported UoW transactions.
- [ ] 3. Implement bounded claims, per-engine progress, retry and stale-work rules.
- [ ] 4. Verify isolated rollback/retry/partial-delivery scenarios when this later exercise is selected.
- [ ] 5. Measure new evidence and filter refresh using the existing evaluation harness.

Before a later implementation commit, reconcile the changed behavior with OpenSpec, domain requirements and relevant ADRs, and record actual verification evidence. No commit or archive is authorized here.
