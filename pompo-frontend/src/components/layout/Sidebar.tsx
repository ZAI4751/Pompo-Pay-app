"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutGroup, m } from "framer-motion";
import { X } from "lucide-react";
import { navGroups } from "./nav-config";
import { PompoMark } from "@/components/brand/PompoMark";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useAppShell } from "./AppShellContext";
import { cn } from "@/lib/utils/cn";
import { pressSpring } from "@/lib/motion";

function NavBody({ onNavigate, scope }: { onNavigate?: () => void; scope: "desktop" | "mobile" }) {
  const pathname = usePathname();
  const { hasPermission } = usePermissions();

  return (
    <>
      <div className="flex h-14 items-center gap-2.5 border-b border-white/10 px-4">
        <PompoMark size={28} />
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Pompo</p>
          <p className="truncate text-sm font-medium text-sidebar-text">Control plane</p>
        </div>
      </div>

      <LayoutGroup id={`${scope}-sidebar-nav`}>
        <nav className="flex-1 overflow-y-auto scrollbar-thin px-2.5 py-4" aria-label="Primary">
          {navGroups.map((group) => {
            const visibleItems = group.items.filter(
              (item) => !item.permission || hasPermission(item.permission),
            );
            if (visibleItems.length === 0) return null;

            return (
              <div key={group.label} className="mb-5">
                <p className="px-2.5 pb-1.5 text-[10px] font-semibold uppercase tracking-[0.16em] text-sidebar-muted">
                  {group.label}
                </p>
                <ul className="space-y-0.5">
                  {visibleItems.map((item) => {
                    const active =
                      pathname === item.href ||
                      (item.href !== "/dashboard" && pathname?.startsWith(`${item.href}/`));
                    const Icon = item.icon;
                    return (
                      <li key={item.href}>
                        <Link
                          href={item.href}
                          onClick={onNavigate}
                          aria-current={active ? "page" : undefined}
                          className={cn(
                            "group relative flex items-center gap-2.5 rounded-sm px-2.5 py-2 text-[13px] transition-colors duration-200",
                            active
                              ? "text-sidebar-active"
                              : "text-sidebar-muted hover:bg-sidebar-hover hover:text-sidebar-text",
                          )}
                        >
                          {active && (
                            <m.span
                              layoutId={`${scope}-nav-active-bg`}
                              className="absolute inset-0 rounded-sm bg-sidebar-active-bg"
                              aria-hidden="true"
                              transition={pressSpring}
                            />
                          )}
                          {active && (
                            <m.span
                              layoutId={`${scope}-nav-active-bar`}
                              className="absolute inset-y-1 left-0 w-0.5 rounded-full bg-primary"
                              aria-hidden="true"
                              transition={pressSpring}
                            />
                          )}
                          <Icon className="relative h-4 w-4 shrink-0" aria-hidden="true" />
                          <span className="relative min-w-0 flex-1 truncate">{item.label}</span>
                          {item.comingSoon && (
                            <span className="relative shrink-0 rounded-sm border border-white/10 px-1.5 py-px text-[9px] font-medium uppercase tracking-wide text-sidebar-muted">
                              Soon
                            </span>
                          )}
                        </Link>
                      </li>
                    );
                  })}
                </ul>
              </div>
            );
          })}
        </nav>
      </LayoutGroup>

      <div className="border-t border-white/10 px-4 py-3">
        <p className="text-[10px] uppercase tracking-[0.16em] text-sidebar-muted">Rail bridge</p>
        <p className="mt-0.5 truncate text-xs text-sidebar-text">Malawi · MWK</p>
      </div>
    </>
  );
}

export function Sidebar() {
  const { mobileNavOpen, closeMobileNav } = useAppShell();

  return (
    <>
      <aside className="hidden w-[232px] shrink-0 flex-col bg-sidebar transition-colors duration-200 md:flex">
        <NavBody scope="desktop" />
      </aside>

      {mobileNavOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-black/60"
            aria-label="Close navigation"
            onClick={closeMobileNav}
          />
          <aside className="relative z-10 flex h-full w-[min(232px,80vw)] flex-col bg-sidebar shadow-glow">
            <button
              type="button"
              onClick={closeMobileNav}
              className="absolute right-2 top-3 rounded p-1 text-sidebar-muted hover:text-sidebar-text"
              aria-label="Close navigation"
            >
              <X className="h-4 w-4" />
            </button>
            <NavBody scope="mobile" onNavigate={closeMobileNav} />
          </aside>
        </div>
      )}
    </>
  );
}
