import React from "react";
import { ToolEventItem } from "@/lib/types";
import { ToolEventRow } from "./ToolEventRow";
import { EmptyState } from "./EmptyState";

export function RunTimeline({ events }: { events: ToolEventItem[] }) {
  if (!events || events.length === 0) {
    return <EmptyState title="No tool events recorded" description="This run did not invoke any tool operations." />;
  }

  return (
    <div className="space-y-3">
      {events.map((ev, i) => (
        <ToolEventRow key={i} event={ev} />
      ))}
    </div>
  );
}
