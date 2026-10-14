import React from "react";

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const normalized = status.toLowerCase();

  let bg = "bg-slate-100 text-slate-700 border-slate-200";
  let dotColor = "bg-slate-400";
  const label = status.replace(/_/g, " ");

  if (["succeeded", "approved", "ok", "active"].includes(normalized)) {
    bg = "bg-emerald-50 text-emerald-800 border-emerald-200";
    dotColor = "bg-emerald-600";
  } else if (["running", "in_progress"].includes(normalized)) {
    bg = "bg-blue-50 text-blue-800 border-blue-200";
    dotColor = "bg-blue-600 animate-pulse";
  } else if (["waiting_approval", "pending", "queued"].includes(normalized)) {
    bg = "bg-amber-50 text-amber-800 border-amber-200";
    dotColor = "bg-amber-600";
  } else if (["failed", "error", "rejected", "expired", "suspended"].includes(normalized)) {
    bg = "bg-red-50 text-red-800 border-red-200";
    dotColor = "bg-red-600";
  }

  return (
    <span
      className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium border capitalize ${bg}`}
    >
      <span className={`w-1.5 h-1.5 rounded-full ${dotColor}`} />
      {label}
    </span>
  );
}
