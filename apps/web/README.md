# AI Operations Agent — web console

Next.js + TypeScript + Tailwind operator console scaffold (TASK-001). Feature screens (assistant, runs, approvals, evaluations, system status) are implemented in later tasks.

## Local commands

```bash
npm ci
npm run dev        # http://localhost:3000
npm run lint
npm run typecheck
npm run build
```

Design tokens follow `docs/DESIGN.md` (`globals.css`). The console talks to the FastAPI backend; it never holds the model key.
