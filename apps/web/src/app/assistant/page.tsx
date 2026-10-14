"use client";

import React, { useState } from "react";
import Link from "next/link";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { RunTimeline } from "@/components/RunTimeline";
import { SourceReference } from "@/components/SourceReference";
import { submitAgentRun, getRunDetails } from "@/lib/api";
import { AgentRunDetails } from "@/lib/types";

export default function AssistantPage() {
  const [prompt, setPrompt] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [runDetails, setRunDetails] = useState<AgentRunDetails | null>(null);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!prompt.trim() || loading) return;

    setLoading(true);
    setError(null);
    try {
      const res = await submitAgentRun(prompt);
      const details = await getRunDetails(res.run_id);
      setRunDetails(details);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to execute request";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const isWaitingApproval = runDetails?.status === "waiting_approval" || runDetails?.approvals?.some((a) => a.status === "pending");

  return (
    <div className="space-y-6">
      <PageHeader
        title="Assistant Console"
        description="Interact with the AI Operations Agent for read-only lookups, searches, calculations, and action proposals."
      />

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Composer Panel */}
        <div className="lg:col-span-1 space-y-6">
          <div className="bg-surface rounded-xl border border-border p-6 shadow-xs">
            <h2 className="text-base font-semibold text-primary mb-3">Request Composer</h2>
            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <textarea
                  rows={4}
                  value={prompt}
                  onChange={(e) => setPrompt(e.target.value)}
                  maxLength={8000}
                  placeholder="e.g. Get info for customer CUST-1001 or propose ticket for billing..."
                  className="w-full rounded-lg border border-border p-3 text-sm text-primary bg-surface focus:outline-hidden focus:ring-2 focus:ring-accent/20 focus:border-accent resize-none font-sans"
                />
                <div className="flex justify-between items-center mt-1 text-xs text-secondary">
                  <span>Max 8,000 chars</span>
                  <span>{prompt.length}/8000</span>
                </div>
              </div>

              <button
                type="submit"
                disabled={loading || !prompt.trim()}
                className="w-full py-2.5 px-4 bg-accent text-white rounded-lg text-sm font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-xs"
              >
                {loading ? "Executing Run..." : "Submit Request"}
              </button>
            </form>
            {error && <p className="text-xs text-red-600 font-medium mt-3">{error}</p>}
          </div>

          <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-3">
            <h3 className="text-xs font-semibold text-secondary uppercase tracking-wider">Example Prompts</h3>
            <ul className="space-y-2 text-xs text-secondary">
              <li>• &quot;Get info for customer CUST-1001&quot;</li>
              <li>• &quot;Retrieve order ORD-5001&quot;</li>
              <li>• &quot;Search internal documents for refund policy&quot;</li>
              <li>• &quot;Calculate 12.50 plus 8.25&quot;</li>
            </ul>
          </div>
        </div>

        {/* Results & Trace Panel */}
        <div className="lg:col-span-2 space-y-6">
          {runDetails ? (
            <>
              {/* Status Banner */}
              <div className="bg-surface rounded-xl border border-border p-5 shadow-xs flex items-center justify-between">
                <div>
                  <span className="text-xs font-mono text-secondary">RUN ID: {runDetails.run_id}</span>
                  <div className="flex items-center gap-2 mt-1">
                    <span className="text-sm font-semibold text-primary">Status:</span>
                    <StatusBadge status={runDetails.status} />
                  </div>
                </div>
                <div className="text-right text-xs text-secondary">
                  <p>Duration: {runDetails.duration_ms} ms</p>
                  <p className="mt-0.5">Model: {runDetails.model_label}</p>
                </div>
              </div>

              {/* Approval Required Notice */}
              {isWaitingApproval && (
                <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 flex items-center justify-between">
                  <div>
                    <h4 className="text-sm font-semibold text-amber-900">Approval Required</h4>
                    <p className="text-xs text-amber-700 mt-0.5">
                      This request has generated a pending action proposal. No ticket or report has been executed yet.
                    </p>
                  </div>
                  <Link
                    href="/approvals"
                    className="px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-medium hover:bg-amber-700 transition-colors shrink-0"
                  >
                    Go to Approval Inbox →
                  </Link>
                </div>
              )}

              {/* Answer Panel */}
              <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-4">
                <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Final Response</h3>
                <div className="p-4 rounded-lg bg-app border border-border text-primary text-sm leading-relaxed whitespace-pre-wrap font-sans">
                  {runDetails.final_answer || "No final answer produced."}
                </div>

                {/* Source references example */}
                {runDetails.timeline.some((t) => t.tool_name === "search_documents") && (
                  <div className="pt-3 border-t border-border flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-medium text-secondary">Citations:</span>
                    <SourceReference sourceId="DOC-REFUND-POLICY" />
                  </div>
                )}
              </div>

              {/* Tool Activity Timeline */}
              <div className="space-y-3">
                <h3 className="text-sm font-semibold text-secondary uppercase tracking-wider">Tool Activity Timeline</h3>
                <RunTimeline events={runDetails.timeline} />
              </div>
            </>
          ) : (
            <div className="bg-surface rounded-xl border border-border p-16 text-center shadow-xs">
              <div className="w-12 h-12 rounded-full bg-accent-surface flex items-center justify-center text-accent mx-auto mb-4 font-bold text-lg">
                AI
              </div>
              <h3 className="text-base font-semibold text-primary">No Active Run Selected</h3>
              <p className="text-sm text-secondary mt-1 max-w-sm mx-auto">
                Submit an operation request using the composer on the left to inspect the run trace, tool events, and structured output.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
