# PY-022 tasks

Phase: Pilot slice, then post-pilot extension. Dependencies: PY-014, PY-018, PY-019 pilot and reusable answer composition from PY-020.

All items below are planned, not implemented by this documentation change.

- [ ] 1. Pilot: define typed application tool schemas and wrap the selected operations through LangChain.
- [ ] 2. Pilot: implement explicit LangGraph state and bounded tool-selection/execution/answer nodes.
- [ ] 3. Pilot: verify exact, hybrid and reference routes using controlled tool-call responses.
- [ ] 4. Pilot: inspect a separately invoked real tool-capable LLM trace, including PostgreSQL final checks.
- [ ] 5. Post-pilot: add clarification/follow-up state and deliberate checkpointing if needed.
- [ ] 6. Post-pilot: compare rewrites, decomposition, repeated retrieval and optional backend strategy selection with PY-017 measurements.

Before a later implementation commit, reconcile the changed behavior with OpenSpec, domain requirements and relevant ADRs, and record actual verification evidence. No commit or archive is authorized here.
