# PY-019 tasks

Phase: Pilot slice, then post-pilot extension. Dependencies: PY-015 for embedding observations; retrieval operations for the connected trace.

All items below are planned, not implemented by this documentation change.

- [ ] 1. Pilot: select one tool-capable provider/model and add explicit configuration and LangChain integration.
- [ ] 2. Pilot: configure Langfuse Cloud Hobby deliberately and capture one connected trace with call/output bounds.
- [ ] 3. Pilot: verify controlled provider orchestration and inspect one separately invoked real model response.
- [ ] 4. Post-pilot: add the second provider and a repeatable comparison configuration.
- [ ] 5. Post-pilot: implement run/case/judge accounting, local limits and reported/estimated reconciliation.
- [ ] 6. Post-pilot: verify budget-stop behavior and preserve local artifacts linked to hosted traces.

Before a later implementation commit, reconcile the changed behavior with OpenSpec, domain requirements and relevant ADRs, and record actual verification evidence. No commit or archive is authorized here.
