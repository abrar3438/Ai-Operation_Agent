import React from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center bg-surface rounded-xl border border-border">
      <div className="w-12 h-12 rounded-full bg-accent-surface flex items-center justify-center text-accent mb-4 font-semibold text-lg">
        ø
      </div>
      <h3 className="text-base font-semibold text-primary">{title}</h3>
      <p className="text-sm text-secondary mt-1 max-w-sm">{description}</p>
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}
