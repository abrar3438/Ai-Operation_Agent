import React from "react";

export function SourceReference({ sourceId }: { sourceId: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-md bg-accent-surface text-accent text-xs font-mono font-medium border border-blue-100">
      <span>📄</span>
      {sourceId}
    </span>
  );
}
