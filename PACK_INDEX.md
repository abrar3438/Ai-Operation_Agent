# Documentation Pack Contents

This pack contains project-planning/context files for Antigravity. It does **not** contain source code or the later task-by-task project prompts.

- `AGENTS.md` — always-on workspace instructions for Antigravity.
- `README.md` — project summary, architecture overview, planned local setup, and release checklist.
- `TASKS.md` — ordered implementation tasks aligned to the supplied Day 36–49 roadmap.
- `.env.example` — placeholder configuration variables only.
- `.gitignore` — ignore rules for local secrets/build artifacts.
- `docs/PRD.md` — project scope, users, user flows, and acceptance criteria.
- `docs/ARCHITECTURE.md` — components, graph flow, tools, data model, API, and failure policy.
- `docs/DESIGN.md` — UI design and interaction system.
- `docs/RULES.md` — development rules for backend, frontend, graph, safety, tests, Git, and documentation.
- `docs/TEST_PLAN.md` — unit/integration/E2E/evaluation/stress test requirements.
- `docs/SECURITY.md` — threat model and security constraints.
- `docs/DECISIONS.md` — planned architecture decisions (ADRs).
- `docs/MEMORY.md` — current status and next task.
- `docs/TECHNICAL_REFERENCES.md` — official documentation links to verify during implementation.

Recommended: extract/copy these files into the root of the new project workspace in Antigravity, then ask Antigravity to read `AGENTS.md` and the required documents before implementing `TASK-001`. Keep `.env.example` in Git and keep `.env` local.

- `ANTIGRAVITY_PROMPTS.md` — Complete, ordered Antigravity implementation prompts from repository inspection through final release audit.
