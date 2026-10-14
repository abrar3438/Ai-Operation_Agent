import React, { useState } from "react";
import { ToolEventItem } from "@/lib/types";
import { StatusBadge } from "./StatusBadge";

export function ToolEventRow({ event }: { event: ToolEventItem }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="border border-border rounded-xl bg-surface p-4 transition-all">
      <div className="flex items-center justify-between cursor-pointer" onClick={() => setExpanded(!expanded)}>
        <div className="flex items-center gap-3">
          <span className="font-mono text-xs text-secondary w-6">#{event.sequence}</span>
          <div>
            <span className="font-medium text-sm text-primary">{event.tool_name || event.stage}</span>
            <span className="text-xs text-secondary ml-2">({event.duration_ms} ms)</span>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge status={event.status} />
          <span className="text-xs text-secondary">{expanded ? "Hide detail" : "View detail"}</span>
        </div>
      </div>
      {expanded && (
        <div className="mt-3 pt-3 border-t border-border text-xs font-mono text-secondary bg-app p-3 rounded-lg overflow-x-auto">
          <p><strong>Stage:</strong> {event.stage}</p>
          <p><strong>Retry count:</strong> {event.retry_count}</p>
          {event.error_category && <p className="text-red-700"><strong>Error Category:</strong> {event.error_category}</p>}
          <p className="mt-1"><strong>Summary:</strong> {event.detail_summary}</p>
        </div>
      )}
    </div>
  );
}
