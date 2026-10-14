import React from "react";

export function LoadingSkeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div className="space-y-3 animate-pulse">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="h-14 bg-slate-100 rounded-xl border border-border" />
      ))}
    </div>
  );
}
