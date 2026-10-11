import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "AI Operations Agent",
  description:
    "Local operator console scaffold for the AI Operations Agent. Features are implemented in later tasks.",
};

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-app px-6 py-16">
      <div className="w-full max-w-xl rounded-xl border border-app bg-surface p-8 shadow-sm">
        <p className="text-xs font-semibold uppercase tracking-widest text-accent">
          AI Operations Agent
        </p>
        <h1 className="mt-2 text-2xl font-semibold text-primary">
          Operator console scaffold
        </h1>
        <p className="mt-3 text-sm leading-6 text-secondary">
          The API, database, cache, and console foundations are wired in
          TASK-001. Assistant, runs, approvals, evaluations, and system-status
          screens arrive in later tasks. No agent features exist yet.
        </p>
        <dl className="mt-6 space-y-2 text-sm">
          <div className="flex items-center justify-between gap-4">
            <dt className="text-secondary">API health</dt>
            <dd className="font-mono text-xs text-primary">/health/live · /health/ready</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-secondary">API (local)</dt>
            <dd className="font-mono text-xs text-primary">http://localhost:8001</dd>
          </div>
          <div className="flex items-center justify-between gap-4">
            <dt className="text-secondary">Task</dt>
            <dd className="font-mono text-xs text-primary">TASK-001</dd>
          </div>
        </dl>
      </div>
    </main>
  );
}
