"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

const navItems = [
  { name: "Assistant", href: "/assistant", icon: "💬" },
  { name: "Runs", href: "/runs", icon: "⚡" },
  { name: "Approvals", href: "/approvals", icon: "🛡️" },
  { name: "Evaluations", href: "/evaluations", icon: "📊" },
  { name: "System Status", href: "/status", icon: "🟢" },
];

export function SidebarNav({ mobile = false, onItemClick }: { mobile?: boolean; onItemClick?: () => void }) {
  const pathname = usePathname();

  return (
    <nav className={mobile ? "space-y-1" : "flex-1 p-4 space-y-1"}>
      {navItems.map((item) => {
        const active = pathname?.startsWith(item.href);
        return (
          <Link
            key={item.href}
            href={item.href}
            onClick={onItemClick}
            className={`flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
              active
                ? "bg-accent-surface text-accent font-semibold"
                : "text-secondary hover:text-primary hover:bg-slate-50"
            }`}
          >
            <span>{item.icon}</span>
            {item.name}
          </Link>
        );
      })}
    </nav>
  );
}
