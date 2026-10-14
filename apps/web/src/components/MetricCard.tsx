import React from "react";

interface MetricCardProps {
  label: string;
  value: string | number;
  subtext?: string;
  trend?: "up" | "down" | "neutral";
}

export function MetricCard({ label, value, subtext }: MetricCardProps) {
  return (
    <div className="bg-surface rounded-xl border border-border p-5 shadow-xs">
      <p className="text-xs font-medium text-secondary uppercase tracking-wider">{label}</p>
      <p className="text-3xl font-semibold text-primary mt-2">{value}</p>
      {subtext && <p className="text-xs text-secondary mt-1">{subtext}</p>}
    </div>
  );
}
