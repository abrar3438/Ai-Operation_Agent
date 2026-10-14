"use client";

import React, { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { listRuns } from "@/lib/api";
import { AgentRunSummary } from "@/lib/types";

export default function RunsPage() {
  const [runs, setRuns] = useState<AgentRunSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("");
  const [modelFilter, setModelFilter] = useState<string>("");

  const loadRuns = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listRuns(statusFilter || undefined, modelFilter || undefined);
      setRuns(data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load run history";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [statusFilter, modelFilter]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadRuns();
  }, [loadRuns]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="Run History"
        description="Inspect historical agent executions, request previews, terminal statuses, and tool metrics."
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-border text-xs bg-surface text-primary font-medium focus:outline-hidden focus:ring-2 focus:ring-accent/20 focus:border-accent"
            >
              <option value="">All Statuses</option>
              <option value="succeeded">Succeeded</option>
              <option value="failed">Failed</option>
              <option value="waiting_approval">Waiting Approval</option>
            </select>
            <input
              type="text"
              placeholder="Filter by model label..."
              value={modelFilter}
              onChange={(e) => setModelFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-border text-xs bg-surface text-primary focus:outline-hidden focus:ring-2 focus:ring-accent/20 focus:border-accent"
            />
            <button
              onClick={() => loadRuns()}
              className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium bg-surface text-primary hover:bg-slate-50 transition-colors"
            >
              Refresh
            </button>
          </div>
        }
      />

      {loading ? (
        <LoadingSkeleton rows={5} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadRuns()} />
      ) : runs.length === 0 ? (
        <EmptyState
          title="No execution runs found"
          description={statusFilter || modelFilter ? "No runs matching the selected filters." : "Submit a request in the assistant console to start your first run."}
        />
      ) : (
        <div className="bg-surface rounded-xl border border-border overflow-hidden shadow-xs">
          <div className="overflow-x-auto">
            <table className="w-full text-left border-collapse min-w-[650px]">
              <thead>
                <tr className="border-b border-border bg-app/50 text-xs font-semibold text-secondary uppercase tracking-wider">
                  <th className="py-3 px-4">Run ID</th>
                  <th className="py-3 px-4">Request Preview</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4">Model</th>
                  <th className="py-3 px-4">Timestamp</th>
                  <th className="py-3 px-4 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {runs.map((r) => (
                  <tr key={r.run_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3.5 px-4 font-mono text-xs text-secondary font-medium">
                      {r.run_id.slice(0, 8)}...
                    </td>
                    <td className="py-3.5 px-4 text-primary font-medium max-w-xs truncate">
                      {r.request_preview}
                    </td>
                    <td className="py-3.5 px-4">
                      <StatusBadge status={r.status} />
                    </td>
                    <td className="py-3.5 px-4 text-xs font-mono text-secondary">{r.model_label}</td>
                    <td className="py-3.5 px-4 text-xs text-secondary">
                      {new Date(r.created_at).toLocaleString()}
                    </td>
                    <td className="py-3.5 px-4 text-right">
                      <Link
                        href={`/runs/${r.run_id}`}
                        className="text-xs font-semibold text-accent hover:underline"
                      >
                        Inspect Trace →
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
