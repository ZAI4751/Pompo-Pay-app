"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Menu, Search } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import { Breadcrumb } from "@/components/ui/Breadcrumb";
import { IconButton } from "@/components/ui/IconButton";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { useAppShell } from "./AppShellContext";
import { useAuth } from "@/lib/auth/AuthContext";

interface TopBarProps {
  title: string;
  breadcrumb?: { label: string; href?: string }[];
  actions?: React.ReactNode;
}

export function TopBar({ title, breadcrumb, actions }: TopBarProps) {
  const { openMobileNav } = useAppShell();
  const { isDemoSession } = useAuth();
  const [searchOpen, setSearchOpen] = useState(false);
  const [notesOpen, setNotesOpen] = useState(false);
  const [query, setQuery] = useState("");
  const searchRef = useRef<HTMLDivElement>(null);
  const notesRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setSearchOpen(false);
      }
      if (notesRef.current && !notesRef.current.contains(event.target as Node)) {
        setNotesOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  return (
    <header className="relative z-30 flex h-14 shrink-0 items-center gap-4 border-b border-border bg-white/80 px-4 pompo-glass transition-colors duration-200 dark:bg-slate-900/80">
      <IconButton aria-label="Open navigation" className="md:hidden" onClick={openMobileNav}>
        <Menu className="h-4 w-4" />
      </IconButton>

      <div className="min-w-0 flex-1">
        {breadcrumb && breadcrumb.length > 0 ? (
          <Breadcrumb items={breadcrumb} />
        ) : (
          <h1 className="truncate text-sm font-semibold text-text">{title}</h1>
        )}
      </div>

      <div ref={searchRef} className="relative hidden max-w-xs flex-1 lg:block">
        <label className="sr-only" htmlFor="pompo-command-search">
          Search
        </label>
        <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-text-subtle" />
        <input
          id="pompo-command-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setSearchOpen(true)}
          placeholder="Search merchants, refs, users"
          className="h-8 w-full rounded-sm border border-border bg-slate-50 pl-8 pr-3 text-xs text-text placeholder:text-text-subtle transition-colors duration-200 focus-visible:border-primary focus-visible:shadow-[0_0_0_3px_color-mix(in_srgb,var(--color-primary)_22%,transparent)] dark:bg-slate-900"
        />
        {searchOpen && (
          <div className="absolute right-0 top-full z-20 mt-1 w-full rounded-sm border border-border bg-surface p-3 text-xs text-text-muted shadow-glow pompo-glass animate-fade-in">
            Search is a visual control-plane affordance. It is not connected to live data in this
            preview.
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <span className="hidden items-center gap-1.5 rounded-sm border border-border px-2 py-1 text-[11px] text-text-muted sm:inline-flex">
          <span className="relative flex h-2 w-2" aria-hidden="true">
            <span className="absolute inset-0 rounded-full bg-success opacity-60 motion-safe:animate-ping" />
            <span className="relative h-2 w-2 rounded-full bg-success motion-safe:animate-pulse-dot" />
          </span>
          Systems
        </span>
        {isDemoSession && <MockDataBadge />}
        {actions}
        <div ref={notesRef} className="relative">
          <IconButton
            aria-label="Notifications"
            onClick={() => setNotesOpen((open) => !open)}
            aria-expanded={notesOpen}
          >
            <Bell className="h-4 w-4" />
          </IconButton>
          {notesOpen && (
            <div
              role="dialog"
              aria-label="Notifications"
              className="absolute right-0 top-full z-20 mt-1 w-72 rounded-sm border border-border bg-surface p-3 shadow-glow pompo-glass animate-fade-in"
            >
              <p className="text-xs font-medium text-text">Operations notices</p>
              <p className="mt-1 text-xs text-text-muted">
                No live notification feed is wired. This panel is a preview of the control-plane
                chrome.
              </p>
            </div>
          )}
        </div>
        <ThemeToggle />
        <div className="mx-1 hidden h-6 w-px bg-border sm:block" aria-hidden="true" />
        <UserMenu />
      </div>
    </header>
  );
}
