import React, { useState } from "react";
import { ApprovalItem } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";
import { ConfirmDialog } from "./ConfirmDialog";

interface ApprovalDecisionPanelProps {
  item: ApprovalItem;
  onDecide: (id: string, decision: "approve" | "reject", reviewer: string) => Promise<void>;
}

export function ApprovalDecisionPanel({ item, onDecide }: ApprovalDecisionPanelProps) {
  const [reviewer, setReviewer] = useState("Operator");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [confirmModal, setConfirmModal] = useState<"approve" | "reject" | null>(null);

  const handleAction = async (decision: "approve" | "reject") => {
    setLoading(true);
    setError(null);
    try {
      await onDecide(item.id, decision, reviewer);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to process decision";
      setError(errorMessage);
    } finally {
      setLoading(false);
      setConfirmModal(null);
    }
  };

  const isPending = item.status === "pending";

  return (
    <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <span className="text-xs font-mono text-secondary">PROPOSAL ID: {item.id}</span>
          <h3 className="text-lg font-semibold text-primary capitalize mt-1">
            {item.action_type.replace(/_/g, " ")}
          </h3>
        </div>
        <StatusBadge status={item.status} />
      </div>

      <div className="text-xs font-mono bg-app p-4 rounded-lg border border-border overflow-x-auto text-primary">
        <p className="font-semibold mb-2 text-secondary">Sanitized Arguments:</p>
        <pre>{JSON.stringify(item.arguments, null, 2)}</pre>
      </div>

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pt-2 border-t border-border">
        <div className="flex items-center gap-2">
          <label className="text-xs font-medium text-secondary">Reviewer Name:</label>
          <input
            type="text"
            value={reviewer}
            onChange={(e) => setReviewer(e.target.value)}
            disabled={!isPending || loading}
            className="px-3 py-1.5 rounded-lg border border-border text-xs bg-surface text-primary focus:outline-hidden focus:ring-2 focus:ring-accent/20 focus:border-accent"
          />
        </div>

        {isPending ? (
          <div className="flex items-center gap-3">
            <button
              onClick={() => setConfirmModal("reject")}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-medium border border-red-200 text-red-700 bg-red-50 hover:bg-red-100 transition-colors disabled:opacity-50"
            >
              Reject Action
            </button>
            <button
              onClick={() => setConfirmModal("approve")}
              disabled={loading}
              className="px-4 py-2 rounded-lg text-xs font-medium text-white bg-accent hover:bg-blue-700 transition-colors disabled:opacity-50"
            >
              {loading ? "Processing..." : "Approve & Execute"}
            </button>
          </div>
        ) : (
          <p className="text-xs text-secondary font-medium">
            Decision finalized by <span className="text-primary font-semibold">{item.reviewer || "Unknown"}</span>
          </p>
        )}
      </div>

      {error && <p className="text-xs text-red-600 font-medium mt-2">{error}</p>}

      <ConfirmDialog
        isOpen={confirmModal !== null}
        title={confirmModal === "approve" ? "Authorize Action Execution" : "Reject Action Proposal"}
        message={
          confirmModal === "approve"
            ? `Are you sure you want to approve '${item.action_type}'? This will invoke the action executor.`
            : `Are you sure you want to reject this proposal? This terminates the action without side effects.`
        }
        confirmLabel={confirmModal === "approve" ? "Approve" : "Reject"}
        isDestructive={confirmModal === "reject"}
        onConfirm={() => confirmModal && handleAction(confirmModal)}
        onCancel={() => setConfirmModal(null)}
      />
    </div>
  );
}
