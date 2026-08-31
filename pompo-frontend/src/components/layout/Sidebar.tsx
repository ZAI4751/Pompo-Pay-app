"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { ChevronDown, ShieldHalf } from "lucide-react";
import { navGroups } from "./nav-config";
import { usePermissions } from "@/lib/auth/usePermissions";
import { cn } from "@/lib/utils/cn";

export function Sidebar() {
  const pathname = usePathname();
  const { hasPermission } = usePermissions();
  const [collapsedGroups, setCollapsedGroups] = useState<Set<string>>(new Set());

  const toggleGroup = (label: string) => {
    setCollapsedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(label)) next.delete(label);
      else next.add(label);
      return next;
    });
  };

  return (
    <aside className="hidden w-64 shrink-0 flex-col border-r border-border bg-surface md:flex">
      <div className="flex h-14 items-center gap-2 border-b border-border px-5">
        <div className="flex h-7 w-7 items-center justify-center rounded bg-primary text-primary-foreground">
          <ShieldHalf className="h-4 w-4" aria-hidden="true" />
        </div>
        <span className="text-sm font-semibold tracking-tight text-text">Pompo Admin</span>
      </div>

      <nav className="flex-1 overflow-y-auto scrollbar-thin px-3 py-4" aria-label="Primary">
        {navGroups.map((group) => {
          const visibleItems = group.items.filter(
            (item) => !item.permission || hasPermission(item.permission),
          );
          if (visibleItems.length === 0) return null;
          const collapsed = collapsedGroups.has(group.label);

          return (
            <div key={group.label || "root"} className="mb-1">
              {group.label && (
                <button
                  onClick={() => toggleGroup(group.label)}
                  className="flex w-full items-center justify-between px-3 py-2 text-xs font-semibold uppercase tracking-wide text-text-subtle hover:text-text-muted"
                  aria-expanded={!collapsed}
                >
                  {group.label}
                  <ChevronDown
                    className={cn("h-3.5 w-3.5 transition-transform", collapsed && "-rotate-90")}
                    aria-hidden="true"
                  />
                </button>
              )}
              {!collapsed && (
                <ul className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const active = pathname === item.href || pathname?.startsWith(`${item.href}/`);
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          aria-current={active ? "page" : undefined}
                          className={cn(
                            "flex items-center gap-2.5 rounded px-3 py-2 text-sm transition-colors",
                            active
                              ? "bg-primary-light text-primary font-medium"
                              : "text-text-muted hover:bg-surface-raised hover:text-text",
                          )}
                        >
                          <Icon className="h-4 w-4 shrink-0" aria-hidden="true" />
                          <span className="flex-1 truncate">{item.label}</span>
                          {item.comingSoon && (
                            <span className="rounded-full border border-border-strong px-1.5 py-0.5 text-[10px] font-medium text-text-subtle">
                              Soon
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              )}
            </div>
          );
        })}
      </nav>
    </aside>
  );
}
