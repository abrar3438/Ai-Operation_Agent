# Security Requirements — AI Operations Agent

## 1. Threat model

Assume user prompts, model responses, retrieved documents, tool arguments, cached values, and provider errors may be malformed or adversarial. A model can misunderstand instructions or attempt to call a tool incorrectly. The system must not depend on a prompt alone to enforce security.

## 2. Authentication and exposure

- MVP is a local single-operator development/demo, not a multi-tenant production service.
- Bind PostgreSQL, Redis, pgAdmin, and development-only administrative ports to localhost by default.
- Do not publicly expose the operations UI/API, pgAdmin, PostgreSQL, or Redis without an explicit deployment access-control design.
- Any remote demo that permits action approval, run creation, or evaluation execution must be protected by authentication/access control and rate limiting. If that protection is not implemented, deploy only as a private preview or disable state-changing operations.
- The approval endpoint must authorize the reviewer server-side; knowledge of an approval ID is not sufficient authorization.

## 3. Secret management

- Keep provider keys, database passwords, and other credentials in environment variables or a proper secret store.
- Commit `.env.example`, never `.env` or `.env.local`.
- Keep model API keys server-side; do not use `NEXT_PUBLIC_` prefixes or send keys to the web client.
- Redact secrets in logs, traces, telemetry, HTTP errors, and evaluation reports.
- Rotate any secret that was accidentally committed or exposed; deleting it from the latest file alone is insufficient.

## 4. Tool permissions and prompt injection

- Maintain an explicit allowlist and typed schema for every tool.
- Never allow arbitrary SQL, shell commands, code evaluation, unrestricted filesystem access, or uncontrolled network requests from the model.
- Keep authorization and action policy in backend service code.
- Treat retrieved document instructions as untrusted content, not system instructions. A document saying “ignore policy” cannot change tool permissions or approval requirements.
- Use narrow repository methods that expose only approved fields; avoid returning full raw records by default.
- Validate both model-generated tool inputs and tool outputs.

## 5. Action approval

- `create_ticket` and `send_report` must generate pending proposal records first.
- No side effect may occur before an authorized approval has been durably stored.
- Revalidate approved payload immediately before execution.
- Use transaction/locking/conditional update semantics as appropriate to ensure one reviewer decision wins and repeated submissions are idempotent.
- Record who approved/rejected, when, and what action type was decided, while minimizing stored personal data.
- If persistence, checkpointing, or reviewer authorization is unavailable, fail closed.
- Keep real external integrations disabled by default. Any later integration requires separate secrets, explicit configuration, tests in a sandbox, and confirmation before enabling live actions.

## 6. Database and API

- Validate request bodies, path/query parameters, page sizes, and input lengths.
- Use parameterized ORM/repository queries; no concatenated SQL from user/model content.
- Apply least-privilege database credentials; use separate credentials for schema migration and application runtime where practical.
- Add sensible indexes and constraints for approval states and idempotency.
- Do not expose stack traces, SQL credentials, environment dumps, or internal prompt content in client responses.
- Configure CORS narrowly for the actual UI origin; do not use wildcard credentialed CORS.
- Apply request/rate limits to expensive model routes and evaluation runs before public deployment.

## 7. Logging, tracing, and data retention

- Use run IDs and structured event categories.
- Log tool name/status/timing/retry count plus sanitized summaries, not whole sensitive records by default.
- Redact authorization headers, API tokens, connection strings, and likely credentials.
- Set retention limits for run payloads, graph checkpoints, and traces before loading real data.
- Evaluation fixtures must be synthetic; do not commit real customer messages or provider outputs containing private data.

## 8. Cache and availability

- Cache only approved read-only data with a TTL and safe keys.
- Never cache approvals or use cache to bypass a fresh authorization/state check.
- Redis cache loss must not make protected actions possible or cause stale authorization.
- If the primary database/checkpointer cannot durably persist an approval, do not execute its action.

## 9. Supply chain and deployment

- Pin/lock dependencies after resolving compatibility; update deliberately rather than using unreviewed dependency changes.
- Use minimal official base images and avoid copying `.env`, local caches, tests, or secrets into runtime images unnecessarily.
- Run containers as a non-root user where practical and keep base images updated.
- Do not deploy directly to production as the first test environment. Verify a private preview, health/readiness, logs, and critical approval flows first.
- Never run destructive database operations, deploy, or connect live external systems without explicit operator approval.

## 10. Security release checklist

- [ ] No secrets in Git or client bundles.
- [ ] Local admin/database ports are not bound publicly by default.
- [ ] Tool registry blocks unknown tools and invalid schemas.
- [ ] No arbitrary SQL/eval/shell tool exists.
- [ ] Approval bypass tests pass for ticket and report actions.
- [ ] Rejected, duplicated, stale, and unauthorized approval decisions are safe.
- [ ] Logs/traces redact secrets and unneeded private data.
- [ ] Cache cannot bypass approval/authorization.
- [ ] Public demo is protected or action-capable endpoints are disabled.
