"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Command, Menu, Search } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import { IconButton } from "@/components/ui/IconButton";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { useAppShell } from "./AppShellContext";
import { useAuth } from "@/lib/auth/AuthContext";

interface TopBarProps {
  title: string;
  breadcrumb?: { label: string; href?: string }[];
  actions?: React.ReactNode;
}

export function TopBar({ title, actions }: TopBarProps) {
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
    const onKey = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        document.getElementById("pompo-command-search")?.focus();
        setSearchOpen(true);
      }
      if (event.key === "Escape") {
        setSearchOpen(false);
        setNotesOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("mousedown", onClick);
      document.removeEventListener("keydown", onKey);
    };
  }, []);

  return (
    <header className="relative z-30 flex h-16 shrink-0 items-center gap-3 border-b border-border bg-white/75 px-4 pompo-glass dark:bg-slate-950/70 sm:px-6">
      <IconButton aria-label="Open navigation" className="md:hidden" onClick={openMobileNav}>
        <Menu className="h-4 w-4" />
      </IconButton>

      <h1 className="min-w-0 max-w-[8.5rem] truncate text-base font-semibold tracking-tight text-text sm:max-w-none sm:text-lg">
        {title}
      </h1>

      <div ref={searchRef} className="relative min-w-0 flex-1">
        <label className="sr-only" htmlFor="pompo-command-search">
          Search
        </label>
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle" />
        <input
          id="pompo-command-search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onFocus={() => setSearchOpen(true)}
          placeholder="Search merchants, payments, users…"
          className="h-10 w-full rounded-full border border-transparent bg-surface-inset pl-10 pr-14 text-sm text-text placeholder:text-text-subtle transition focus-visible:border-primary focus-visible:bg-white dark:bg-slate-900"
        />
        <span className="pointer-events-none absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-0.5 rounded-md border border-border px-1.5 py-0.5 text-[10px] font-semibold text-text-subtle sm:inline-flex">
          <Command className="h-3 w-3" />K
        </span>
        {searchOpen && (
          <div className="absolute inset-x-0 top-full z-20 mt-2 rounded-2xl border border-border bg-surface p-3 text-xs text-text-muted shadow-glow pompo-glass">
            Jump-to search is chrome only. Use Merchants, Payments, or Users to query live records.
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5">
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
              className="absolute right-0 top-full z-20 mt-2 w-72 rounded-2xl border border-border bg-surface p-4 shadow-glow pompo-glass"
            >
              <p className="text-sm font-semibold text-text">Operations notices</p>
              <p className="mt-1 text-xs text-text-muted">
                No notification inbox exists yet. Health and rail state live on this dashboard.
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
