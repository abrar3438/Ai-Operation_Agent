"use client";

import React, { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { MetricCard } from "@/components/MetricCard";
import { triggerEvaluation } from "@/lib/api";
import { EvaluationReport } from "@/lib/types";

export default function EvaluationsPage() {
  const [report, setReport] = useState<EvaluationReport | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleRunEval = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await triggerEvaluation();
      setReport(data);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to execute evaluation suite";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Evaluation Suite"
        description="Run versioned scenario datasets, measure task success, tool selection accuracy, safety compliance, and latency percentiles."
        actions={
          <button
            onClick={handleRunEval}
            disabled={loading}
            className="px-4 py-2 bg-accent text-white rounded-lg text-xs font-medium hover:bg-blue-700 transition-colors disabled:opacity-50 shadow-xs"
          >
            {loading ? "Running Evaluation..." : "Run Evaluation Suite"}
          </button>
        }
      />

      {error && (
        <div className="p-4 bg-red-50 border border-red-200 rounded-xl text-red-700 text-xs font-medium">
          {error}
        </div>
      )}

      {report ? (
        <div className="space-y-6">
          {/* Metrics Grid */}
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <MetricCard
              label="Task Completion Rate"
              value={`${report.metrics.task_completion_rate.toFixed(1)}%`}
              subtext={`${report.metrics.passed_cases} of ${report.metrics.total_cases} passed`}
            />
            <MetricCard
              label="Safety Policy Violations"
              value={report.metrics.safety_policy_violations}
              subtext="Separate safety metric"
            />
            <MetricCard
              label="Median Latency"
              value={`${report.metrics.latency_median_ms.toFixed(1)} ms`}
            />
            <MetricCard
              label="P95 Latency"
              value={`${report.metrics.latency_p95_ms.toFixed(1)} ms`}
            />
          </div>

          {/* Results Table */}
          <div className="bg-surface rounded-xl border border-border overflow-hidden shadow-xs">
            <div className="p-4 border-b border-border bg-app/50 flex items-center justify-between">
              <h3 className="text-sm font-semibold text-primary">Scenario Results ({report.metrics.dataset_version})</h3>
              <span className="text-xs text-secondary">Model: {report.metrics.model_label}</span>
            </div>
            <table className="w-full text-left border-collapse">
              <thead>
                <tr className="border-b border-border bg-app/30 text-xs font-semibold text-secondary uppercase tracking-wider">
                  <th className="py-3 px-4">Scenario ID</th>
                  <th className="py-3 px-4">Terminal Status</th>
                  <th className="py-3 px-4">Tools Used</th>
                  <th className="py-3 px-4">Latency</th>
                  <th className="py-3 px-4 text-right">Outcome</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border text-sm">
                {report.results.map((res) => (
                  <tr key={res.scenario_id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="py-3 px-4 font-mono text-xs font-medium text-primary">{res.scenario_id}</td>
                    <td className="py-3 px-4 text-xs font-mono text-secondary">{res.status}</td>
                    <td className="py-3 px-4 text-xs font-mono text-secondary">{res.used_tools.join(", ") || "None"}</td>
                    <td className="py-3 px-4 text-xs text-secondary">{res.latency_ms.toFixed(1)} ms</td>
                    <td className="py-3 px-4 text-right">
                      <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium ${res.success ? "bg-emerald-50 text-emerald-800" : "bg-red-50 text-red-800"}`}>
                        {res.success ? "Passed" : "Failed"}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Known Limitations */}
          <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-2">
            <h4 className="text-xs font-semibold text-secondary uppercase tracking-wider">Known Limitations</h4>
            <ul className="list-disc list-inside text-xs text-secondary space-y-1">
              {report.known_limitations.map((lim, i) => (
                <li key={i}>{lim}</li>
              ))}
            </ul>
          </div>
        </div>
      ) : (
        <div className="bg-surface rounded-xl border border-border p-16 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-accent-surface flex items-center justify-center text-accent mx-auto mb-4 font-bold text-lg">
            📊
          </div>
          <h3 className="text-base font-semibold text-primary">No Evaluation Run Executed Yet</h3>
          <p className="text-sm text-secondary mt-1 max-w-sm mx-auto">
            Click &quot;Run Evaluation Suite&quot; above to execute the versioned scenario suite against the backend and compute quality & safety metrics.
          </p>
        </div>
      )}
    </div>
  );
}
