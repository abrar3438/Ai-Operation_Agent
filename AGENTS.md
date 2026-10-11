# Antigravity Project Instructions — AI Operations Agent

This is a Python/FastAPI + LangGraph agent with a Next.js/TypeScript operator console. **Read the project documents before changing code.**

## Required context

Before implementation, read:
- `docs/PRD.md` — what is in/out of scope and how success is measured.
- `docs/ARCHITECTURE.md` — system boundaries, graph flow, data model, and tool contracts.
- `docs/DESIGN.md` — UI visual and interaction rules.
- `docs/RULES.md` — coding, testing, and repository rules.
- `TASKS.md` — the next unchecked task and its acceptance criteria.
- `docs/TEST_PLAN.md` and `docs/SECURITY.md` — verification and safety obligations.
- `docs/DECISIONS.md` and `docs/MEMORY.md` — existing decisions and current state.

## Operating rules

1. Do not implement multiple unrelated tasks in one change. Select one task ID from `TASKS.md` and follow read → understand → plan → implement → test → review → fix → commit → document.
2. For tasks that touch several components, first inspect the repository and return a short implementation plan. Do not modify files until the plan is clear.
3. Do not replace the chosen stack, introduce a second database layer, or add new infrastructure without a documented reason and an ADR in `docs/DECISIONS.md`.
4. Never expose API keys, database credentials, user secrets, or unredacted sensitive payloads. Use `.env.example` for names/placeholders only.
5. Only expose allowlisted tools. Validate model-generated arguments with Pydantic (or an equally explicit schema) before running a tool. Never allow unrestricted LLM-generated SQL or shell commands.
6. `create_ticket` and `send_report` are side-effecting tools. A model request must create a pending approval record and pause the graph; neither action may execute until an authorized operator approves it. Rejections must terminate that action without side effects. Keep the default adapters mocked and use synthetic seed data.
7. Enforce graph step limits, per-tool timeouts, bounded retries, typed errors, and predictable terminal states. Do not retry permanent validation/authorization errors as though they were transient.
8. Cache only deterministic, read-only tool results. Never cache approvals, mutations, personal data without a reviewed policy, or action outcomes in a way that can bypass authorization.
9. Add tests with every behavior change. Run the smallest relevant test set first, then the broader quality gates available in the repository. Do not claim tests passed unless you ran them and saw the successful exit status.
10. Keep the frontend responsive and accessible. Reuse existing components and follow `docs/DESIGN.md`; do not redesign unrelated screens.
11. Update `TASKS.md`, `docs/MEMORY.md`, and relevant documentation after completing a task. Record architecture changes in `docs/DECISIONS.md`.
12. Do not run destructive commands, wipe local databases, deploy to production, or contact real external systems without explicit user approval.

## Task completion response

After each task, report: task ID; files changed; behavior implemented; commands/tests actually run and their outcomes; security/approval implications; known limitations; and the exact next unchecked task. Do not silently continue to the next task.
