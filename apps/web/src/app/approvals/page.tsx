"use client";

import React, { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { ApprovalDecisionPanel } from "@/components/ApprovalDecisionPanel";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { ErrorState } from "@/components/ErrorState";
import { EmptyState } from "@/components/EmptyState";
import { listApprovals, decideApproval } from "@/lib/api";
import { ApprovalItem } from "@/lib/types";

export default function ApprovalsPage() {
  const [approvals, setApprovals] = useState<ApprovalItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>("pending");

  const loadApprovals = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listApprovals(statusFilter || undefined);
      setApprovals(data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to load approval inbox";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadApprovals();
  }, [loadApprovals]);

  const handleDecide = async (id: string, decision: "approve" | "reject", reviewer: string) => {
    await decideApproval(id, decision, reviewer);
    await loadApprovals();
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Approval Inbox"
        description="Review, approve, or reject pending action proposals (create_ticket and send_report) before execution."
        actions={
          <div className="flex items-center gap-2">
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-3 py-1.5 rounded-lg border border-border text-xs bg-surface text-primary font-medium focus:outline-hidden focus:ring-2 focus:ring-accent/20 focus:border-accent"
            >
              <option value="">All Statuses</option>
              <option value="pending">Pending</option>
              <option value="approved">Approved</option>
              <option value="rejected">Rejected</option>
              <option value="expired">Expired</option>
            </select>
            <button
              onClick={() => loadApprovals()}
              className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium bg-surface text-primary hover:bg-slate-50 transition-colors"
            >
              Refresh
            </button>
          </div>
        }
      />

      {loading ? (
        <LoadingSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadApprovals()} />
      ) : approvals.length === 0 ? (
        <EmptyState
          title="No approval proposals found"
          description={statusFilter ? `No proposals matching status '${statusFilter}'.` : "When the agent proposes tickets or reports, they will appear here for review."}
        />
      ) : (
        <div className="space-y-4">
          {approvals.map((item) => (
            <ApprovalDecisionPanel key={item.id} item={item} onDecide={handleDecide} />
          ))}
        </div>
      )}
    </div>
  );
}
