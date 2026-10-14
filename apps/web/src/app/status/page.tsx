"use client";

import React, { useCallback, useEffect, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { StatusBadge } from "@/components/StatusBadge";
import { ErrorState } from "@/components/ErrorState";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { fetchHealth } from "@/lib/api";
import { HealthStatusResponse } from "@/lib/types";

export default function StatusPage() {
  const [live, setLive] = useState<HealthStatusResponse | null>(null);
  const [ready, setReady] = useState<HealthStatusResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadHealth = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchHealth();
      setLive(data.live);
      setReady(data.ready);
    } catch (err: unknown) {
      const errorMessage = err instanceof Error ? err.message : "Failed to reach backend services";
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    loadHealth();
  }, [loadHealth]);

  return (
    <div className="space-y-6">
      <PageHeader
        title="System Status"
        description="Monitor backend liveness, database readiness, Redis cache status, and provider connectivity without exposing secrets."
        actions={
          <button
            onClick={() => loadHealth()}
            className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium bg-surface text-primary hover:bg-slate-50 transition-colors"
          >
            Refresh Status
          </button>
        }
      />

      {loading ? (
        <LoadingSkeleton rows={3} />
      ) : error ? (
        <ErrorState message={error} onRetry={() => loadHealth()} />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Liveness & Readiness Summary */}
          <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-primary">Service Health</h2>
            <div className="space-y-3">
              <div className="flex items-center justify-between p-3 rounded-lg bg-app border border-border">
                <span className="text-sm font-medium text-primary">API Liveness (/health/live)</span>
                <StatusBadge status={live ? "succeeded" : "failed"} />
              </div>
              <div className="flex items-center justify-between p-3 rounded-lg bg-app border border-border">
                <span className="text-sm font-medium text-primary">API Readiness (/health/ready)</span>
                <StatusBadge status={ready?.status || "degraded"} />
              </div>
            </div>
          </div>

          {/* Dependencies Detail */}
          <div className="bg-surface rounded-xl border border-border p-6 shadow-xs space-y-4">
            <h2 className="text-base font-semibold text-primary">Dependency Diagnostics</h2>
            {ready?.dependencies && ready.dependencies.length > 0 ? (
              <div className="space-y-3">
                {ready.dependencies.map((dep, i) => (
                  <div key={i} className="flex items-center justify-between p-3 rounded-lg bg-app border border-border">
                    <div>
                      <p className="text-sm font-medium text-primary capitalize">{dep.name}</p>
                      <p className="text-xs text-secondary">Required: {dep.required ? "Yes" : "Optional"}</p>
                    </div>
                    <StatusBadge status={dep.status} />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-xs text-secondary">Readiness diagnostics unavailable or service offline.</p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
