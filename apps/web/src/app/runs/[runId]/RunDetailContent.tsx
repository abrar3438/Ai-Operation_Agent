"use client";

import React, { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { RunTimeline } from "@/components/RunTimeline";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { ErrorState } from "@/components/ErrorState";
import { getRunDetails } from "@/lib/api";
import { AgentRunDetails } from "@/lib/types";

export function RunDetailContent() {
  const params = useParams();
  const runId = params?.runId as string;

  const [details, setDetails] = useState<AgentRunDetails | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!runId) return;
    async function load() {
      try {
        const data = await getRunDetails(runId);
        setDetails(data);
      } catch (err: unknown) {
        const errorMessage = err instanceof Error ? err.message : "Failed to load run details";
        setError(errorMessage);
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [runId]);

  if (loading) return <LoadingSkeleton rows={4} />;
  if (error || !details) return <ErrorState message={error || "Run not found"} />;

  return (
    <div className="space-y-6">
      <div className="mb-2">
        <Link href="/runs" className="text-xs font-semibold text-accent hover:underline">
          ← Back to Run History
        </Link>
      </div>

      <PageHeader
        title={`Run Trace: ${details.run_id}`}
        description={`Thread ID: ${details.thread_id}`}
        actions={<StatusBadge status={details.status} />}
      />

      {/* Summary Grid */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-surface rounded-xl border border-border p-4 shadow-xs">
          <p className="text-xs text-secondary uppercase tracking-wider font-medium">Duration</p>
          <p className="text-xl font-semibold text-primary mt-1">{details.duration_ms} ms</p>
        </div>
        <div className="bg-surface rounded-xl border border-border p-4 shadow-xs">
          <p className="text-xs text-secondary uppercase tracking-wider font-medium">Tool Calls</p>
          <p className="text-xl font-semibold text-primary mt-1">{details.tool_call_count}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border p-4 shadow-xs">
          <p className="text-xs text-secondary uppercase tracking-wider font-medium">Model</p>
          <p className="text-sm font-mono font-semibold text-primary mt-1 truncate">{details.model_label}</p>
        </div>
        <div className="bg-surface rounded-xl border border-border p-4 shadow-xs">
          <p className="text-xs text-secondary uppercase tracking-wider font-medium">Provider</p>
          <p className="text-sm font-mono font-semibold text-primary mt-1 capitalize">{details.provider_label}</p>
        </div>
      </div>

      {/* Request & Final Answer */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-2">
          <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">User Request</h3>
          <p className="text-sm text-primary font-medium bg-app p-3 rounded-lg border border-border">
            {details.request_preview}
          </p>
        </div>
        <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-2">
          <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">Final Answer</h3>
          <div className="text-sm text-primary bg-app p-3 rounded-lg border border-border whitespace-pre-wrap font-sans">
            {details.final_answer || "No final answer produced."}
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="space-y-3">
        <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Chronological Tool Timeline</h3>
        <RunTimeline events={details.timeline} />
      </div>
    </div>
  );
}
