"use client";

import React, { Suspense, useState } from "react";
import { SidebarNav } from "./SidebarNav";

interface AppShellProps {
  children: React.ReactNode;
}

export function AppShell({ children }: AppShellProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <div className="min-h-screen bg-app flex flex-col md:flex-row text-primary font-sans">
      {/* Desktop Sidebar */}
      <aside className="hidden md:flex flex-col w-64 bg-surface border-r border-border shrink-0">
        <div className="p-6 border-b border-border flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg bg-accent text-white flex items-center justify-center font-semibold text-sm">
            AI
          </div>
          <div>
            <h2 className="text-sm font-semibold text-primary tracking-tight">Operations Agent</h2>
            <p className="text-xs text-secondary">Control & Audit Console</p>
          </div>
        </div>

        <Suspense fallback={<div className="p-4 text-xs text-secondary">Loading navigation...</div>}>
          <SidebarNav />
        </Suspense>

        <div className="p-4 border-t border-border">
          <div className="bg-app rounded-lg p-3 border border-border">
            <p className="text-xs font-semibold text-primary">Environment</p>
            <p className="text-xs text-secondary mt-0.5">Development (CraftX AI)</p>
          </div>
        </div>
      </aside>

      {/* Mobile Header */}
      <div className="md:hidden flex items-center justify-between bg-surface border-b border-border px-4 py-3">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-accent text-white flex items-center justify-center font-semibold text-xs">
            AI
          </div>
          <span className="font-semibold text-sm text-primary">Operations Agent</span>
        </div>
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="p-2 rounded-lg border border-border text-secondary hover:text-primary"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? "✕" : "☰"}
        </button>
      </div>

      {/* Mobile Dropdown */}
      {mobileMenuOpen && (
        <div className="md:hidden bg-surface border-b border-border p-4 space-y-1">
          <Suspense fallback={null}>
            <SidebarNav mobile onItemClick={() => setMobileMenuOpen(false)} />
          </Suspense>
        </div>
      )}

      {/* Main Content */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <div className="max-w-7xl w-full mx-auto p-6 md:p-10 flex-1">{children}</div>
      </main>
    </div>
  );
}
