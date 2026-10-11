# Development Rules — AI Operations Agent

## 1. General workflow

- Work on one `TASK-###` at a time from `TASKS.md`.
- Before coding: inspect the current repository, read relevant docs, identify affected files, state assumptions, and describe a bounded plan.
- Prefer the smallest coherent change. Do not refactor unrelated code or overwrite user work.
- After code changes: inspect the diff, run relevant tests/checks, report actual outcomes, update docs, then stop for review before moving to another task.
- If documentation conflicts with implemented behavior, do not silently pick one: explain the discrepancy and update the appropriate decision/specification after resolving it.

## 2. Backend rules

- Use Python type hints, focused functions/classes, Pydantic validation at API/tool boundaries, and clear domain types.
- Keep FastAPI routers thin. Put business rules in services, data access in repositories, graph orchestration in agent modules, and provider logic in adapters.
- Do not put all logic into one `main.py` or one large graph node.
- Use SQLAlchemy/repositories for database access and Alembic migrations for schema changes. Do not manually mutate production schema.
- Do not generate SQL from model strings and execute it. Map model intent to preapproved query filters/operations.
- Avoid `eval`, `exec`, shell access, arbitrary filesystem tools, and unrestricted network tools.
- Use an injected/fake model adapter for deterministic unit tests. A normal unit-test run should not need a paid external model call.
- Give each run/tool execution a bounded timeout, explicit outcome, and structured error category.
- Retries are bounded and apply only to transient failures. Validation, authorization, and policy failures are not retryable by default.
- Use idempotency on action proposals and action execution to protect against retries and graph resume behavior.

## 3. LangGraph and agent rules

- Graph state must be explicitly typed/documented and contain only required data.
- Use an allowlisted tool registry; validate tool name and arguments before dispatch and validate tool outputs before adding them to state.
- Every path must reach a terminal result or a deliberate persisted human-approval pause.
- Set maximum graph steps/tool calls and output/context limits; a run may not loop indefinitely.
- Keep application policy outside model prompts. Prompt instructions are not a substitute for backend validation or authorization.
- Store structured observations and source IDs where possible, not only concatenated prose.
- Treat model-generated text/tool arguments as untrusted input.
- Do not claim that a tool or action succeeded until its handler/persistence layer confirms success.

## 4. Human-approval rules

- `create_ticket` and `send_report` must create a pending proposal first. They may not execute as a direct result of an LLM tool call.
- Approval is enforced server-side. Frontend visibility or disabled buttons do not provide security.
- Revalidate the proposed payload and authorization when the operator approves it.
- Use a durable approval state/checkpoint; if approval state cannot be persisted, fail closed and do not execute.
- Permit only valid state transitions. Duplicate or late decisions must be idempotent and must not cause duplicate actions.
- Rejecting an action must cause no side effect and should produce a trace event.
- Keep live third-party integrations out of the MVP; mocked adapters only unless a separately scoped, explicitly approved task is accepted.

## 5. Model provider and secrets

- Read provider, base URL, model, timeout, and key from environment/configuration; do not hardcode them.
- Keep provider-specific request/response code isolated behind a small interface.
- Do not print environment variables, authorization headers, raw HTTP requests with secrets, or model/provider keys in exception messages.
- Never commit `.env`, database dumps, local traces containing sensitive data, or API responses that include secrets.
- `.env.example` must contain blank or clearly fake placeholders only.
- A compatible base URL is not proof that a provider supports the same API semantics; document and test each supported adapter.

## 6. Database and cache rules

- Use migrations; add constraints/indexes where required by access patterns and state transitions.
- Seed data must be synthetic and repeatable. Seed/reset commands must clearly document whether they alter data.
- Use transactions for approval and action state transitions where practical.
- Cache only approved read-only results with TTL and safe, complete cache keys.
- Cache failures must degrade gracefully. Never use cache to skip approval, authorization, or current state checks.
- Bind local database/Redis/admin ports to localhost for development unless the deployment design explicitly requires something else.

## 7. Frontend rules

- Use TypeScript strictness and typed API contracts.
- Keep API/database/business logic out of UI components; centralize typed API clients and error handling.
- Follow `docs/DESIGN.md`, reuse components, and preserve existing visual patterns.
- Implement loading, empty, error, disabled, success, and pending-approval states for each user flow.
- Use semantic HTML, accessible form labels, keyboard support, and visible focus states.
- Never persist a provider key or database credential in frontend code or client-exposed environment variables.
- Do not show action success optimistically before server confirmation.

## 8. Testing and quality gates

- Add or update a test for every behavior change, particularly security and approval logic.
- Run the smallest relevant tests while iterating, then available broad checks before closing a task.
- Expected project commands should be documented in the actual package scripts/pyproject after setup; do not invent a passing result if a script is missing.
- Keep tests deterministic with fakes, synthetic fixtures, and controlled clocks/timeouts where appropriate.
- Use Playwright for the critical operator journeys when the UI is implemented.
- Evaluation scores must come from the evaluation runner; never fabricate benchmark results.

## 9. Observability and data handling

- Use a correlation/run ID across API logs, graph events, and tool events.
- Log tool name, status, duration, retry count, and safe summaries; redact secrets and unnecessary personal data.
- Don't dump complete model prompts, complete customer records, or raw document contents into logs by default.
- Distinguish model answer failure, tool failure, policy rejection, user rejection, and infrastructure failure.

## 10. Git and documentation

- Review `git diff` and `git status` before staging.
- Use small descriptive commits, e.g. `feat(agent): add bounded tool routing` or `test(approval): prevent execution before review`.
- Do not rewrite history, force push, deploy, reset a database, or delete files without explicit user approval.
- Update `TASKS.md`, `docs/MEMORY.md`, README, `docs/TEST_PLAN.md`, and `docs/DECISIONS.md` where relevant.
