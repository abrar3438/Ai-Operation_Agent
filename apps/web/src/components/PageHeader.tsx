import React from "react";

interface PageHeaderProps {
  title: string;
  description: string;
  actions?: React.ReactNode;
}

export function PageHeader({ title, description, actions }: PageHeaderProps) {
  return (
    <div className="flex flex-col md:flex-row md:items-center md:justify-between pb-6 mb-6 border-b border-border gap-4">
      <div>
        <h1 className="text-2xl font-semibold text-primary tracking-tight">{title}</h1>
        <p className="text-sm text-secondary mt-1">{description}</p>
      </div>
      {actions && <div className="flex items-center gap-3">{actions}</div>}
    </div>
  );
}
