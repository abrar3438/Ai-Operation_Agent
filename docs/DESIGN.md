# Design System — AI Operations Agent

## 1. Product feel

Build a calm, professional operations console: clear hierarchy, compact but readable data density, neutral surfaces, and restrained blue accent color. This is a tool for understanding and controlling agent runs—not a flashy chatbot landing page. Prioritize the trace, status, and approval details over decorative effects.

## 2. Visual system

- **Typography:** Inter or the default Geist family provided by the chosen Next.js setup. Use a consistent type scale.
- **Palette:**
  - App background: `#F6F8FB`
  - Main surface: `#FFFFFF`
  - Primary text: `#172033`
  - Secondary text: `#5B667A`
  - Borders: `#E2E8F0`
  - Primary accent: `#315EFB`
  - Subtle accent surface: `#EEF2FF`
  - Success: `#16794B`
  - Warning/pending: `#9A6700`
  - Error/destructive: `#B42318`
- Use semantic tokens rather than scattered literal colors.
- Avoid excessive gradients, glassmorphism, giant hero sections, and different card styles across pages.
- Use icons only when they improve recognition; pair important status colors with readable labels.

## 3. Layout and navigation

### Main shell
- Left navigation on desktop with product mark/name and: Assistant, Runs, Approvals, Evaluations, System Status.
- Main content region with page title, one-sentence context, and relevant actions.
- On small screens, use a compact collapsible navigation and stack detail panels vertically.
- Keep consistent content widths, spacing, table density, and breadcrumbs across pages.

### Assistant console
- Request composer with visible character limit and submit/loading state.
- Run status banner: queued/running/waiting for approval/succeeded/failed/cancelled.
- Answer panel with source references and clear separation between the final answer and trace details.
- Tool activity timeline showing registered tool name, outcome, duration, and retries.
- Pending approval is visible as a distinct state; never imply a proposed action has already executed.

### Run history
- Search/filter by status, time range, and run ID.
- Table columns: run ID, request preview, status, start time/duration, tool-call count.
- Include loading skeleton, no-runs state, filter-no-results state, and retryable API error state.

### Run detail / trace
- Summary header with status and terminal reason.
- Timeline in chronological order; each event has stage/tool, outcome, duration, and a collapsible sanitized detail view.
- Show model/provider label only; never show API keys or secret environment values.
- Highlight retries and failures without making the rest of the trace unreadable.

### Approval inbox
- Show action type, short business reason, requester/run ID, created time, and current status.
- Detail view displays the exact proposed effect and sanitized parameters before decision.
- Approve and reject are separate, clearly labeled actions with confirmation for consequential decisions.
- Disable decision controls while a request is processing or already decided. Show a clear result after the API confirms the decision.
- No optimistic UI may claim an action executed before the backend confirms the execution result.

### Evaluation view
- Show dataset version, run time, tested model/provider label, overall task score, policy compliance, tool-selection accuracy, latency, and failing cases.
- Separate answer-quality metrics from safety policy metrics.
- If no evaluation exists yet, explain how to run one rather than displaying invented placeholder scores.

### System status
- Show health status for API, PostgreSQL, Redis, and provider configuration as available.
- Use neutral text when a provider has not been configured. Never show secret values.

## 4. Interaction rules

- Every action needs hover/focus/disabled states where applicable.
- Provide explicit loading, success, empty, error, and pending states.
- Destructive or consequential operations require a confirmation step and a clear explanation of what will happen.
- Use non-blocking toast/status messaging for routine feedback, but keep important approval and run states visible in the page.
- Tables must support keyboard focus; forms must have visible labels and inline validation messages.
- Do not rely on color alone to communicate state; include status text/icons.
- Avoid layout shifts when status updates arrive.

## 5. Accessibility and responsiveness

- Target WCAG 2.2 AA where practical: contrast, focus visibility, keyboard navigation, semantic landmarks, labels, and error association.
- At approximately 375px width, navigation and action controls remain usable; tables may switch to stacked cards or horizontal scrolling with accessible behavior.
- At tablet widths, trace and detail panels stack rather than squeezing text.
- At desktop widths, use a balanced two-column layout for run details if it improves scanning.
- Respect reduced-motion preferences and avoid auto-playing animation.

## 6. Reusable components

Create/reuse shared components for: `AppShell`, `PageHeader`, `StatusBadge`, `MetricCard`, `DataTable`, `EmptyState`, `ErrorState`, `LoadingSkeleton`, `RunTimeline`, `ToolEventRow`, `ApprovalDecisionPanel`, `SourceReference`, and `ConfirmDialog`. Keep business logic out of presentational components.

## 7. Content tone

Use direct, precise language. Distinguish facts returned by tools, agent-generated summaries, pending proposals, approved actions, completed actions, and failures. Prefer “Approval required” over vague language such as “Action ready.” Never show a success checkmark until the backend reports actual success.
