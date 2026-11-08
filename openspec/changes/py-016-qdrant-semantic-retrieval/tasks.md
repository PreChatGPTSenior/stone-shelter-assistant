# PY-016 tasks

Phase: Pilot: vector retrieval. Dependencies: PY-011 and PY-015.

All items below are planned, not implemented by this documentation change.

- [x] 1a. Add the local Qdrant Compose service with a separate persistent volume and loopback host port.
- [ ] 1b. Add settings, async client ownership and Testcontainers fixtures.
- [ ] 2. Define collections and payload fields using the chosen embedding dimension/metric.
- [ ] 3. Implement vector upsert and filtered operational/reference retrieval.
- [ ] 4. Verify real point identity, filters and query results using controlled vectors, then inspect an explicitly invoked real embedding search.

Before a later implementation commit, reconcile the changed behavior with OpenSpec, domain requirements and relevant ADRs, and record actual verification evidence. No commit or archive is authorized here.
