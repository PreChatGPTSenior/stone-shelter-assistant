# Agent instructions

- This is a learning project. Read `docs/project-manifesto.md`, `docs/task-log.md`, and `docs/adr.md` before planning work. Keep the first working search pilot ahead of production concerns.
- The owner writes Python application code to learn. Explain and review it; edit application code or tests only when explicitly asked. Treat the owner as an experienced Java developer learning Python and AI frameworks.
- Check the installed stack and relevant code before recommending changes. Prefer idiomatic, typed Python and small components with a concrete role.
- Read and follow [Repository organization](docs/repository-organization.md) before adding, moving, or reorganizing code or fixtures.
- The fictional pet-rock premise is intentional. Distinguish authored world facts from geological reference material.
- Keep PostgreSQL authoritative for operational records. Do not infer current adoption status from case events or invent missing source data.
- Run automated database and search integration tests only against disposable Testcontainers, never against the persistent local application database. Do not delete local data or volumes without an explicit request.
- Prefer meaningful scenario tests to tests that repeat implementation details. Keep the first pilot on a visible happy path; defer queues, retries, recovery frameworks, and broad negative-path matrices until selected as learning tasks.
- Write repository documentation, comments, examples, issue descriptions, and commit messages in English.
- Never create, edit, move, rename, or delete the root `README.md` unless the owner explicitly asks for that specific change. The owner maintains the repository's front-page README; other README files are not covered by this restriction.
- Keep project context compact: `docs/project-manifesto.md`, `docs/task-log.md`, `docs/adr.md`, `docs/setup.md`, and `docs/repository-organization.md`. Do not recreate OpenSpec or expand documentation without an explicit request.
- Before every commit, review `docs/task-log.md` against the actual changes and verification results. Add or update affected tasks, move newly completed tasks into the `Done` section at the top, and mark `[x]` only for behavior that has been implemented and observed. Follow the Task Log workflow: pick any backlog item, agree on scope, and assign the next unused ID when moving it to `Current`. Keep future items unnumbered in `Backlog`. Retain IDs when moving completed work to `Done`. Include the updated Task Log in the same commit as the work it describes; if no task state changed, confirm that the log is still accurate. Update `docs/adr.md` only when a decision changes.
- Do not commit, push, or merge without an explicit request.
