"use client";

import { useEffect, useRef, useState } from "react";
import { Bell, Menu, Search, Activity } from "lucide-react";
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
    <header className="flex h-14 shrink-0 items-center gap-3 border-b border-border bg-surface/90 px-4 backdrop-blur-md">
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
          className="h-8 w-full rounded-sm border border-border bg-surface-inset pl-8 pr-3 text-xs text-text placeholder:text-text-subtle"
        />
        {searchOpen && (
          <div className="absolute right-0 top-full z-20 mt-1 w-full rounded-sm border border-border bg-surface p-3 text-xs text-text-muted shadow-md animate-fade-in">
            Search is a visual control-plane affordance. It is not connected to live data in this
            preview.
          </div>
        )}
      </div>

      <div className="flex items-center gap-1.5">
        <span className="hidden items-center gap-1.5 rounded-sm border border-border px-2 py-1 text-[11px] text-text-muted sm:inline-flex">
          <Activity className="h-3 w-3 text-success" aria-hidden="true" />
          <span className="h-1.5 w-1.5 animate-pulse-dot rounded-full bg-success" />
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
              className="absolute right-0 top-full z-20 mt-1 w-72 rounded-sm border border-border bg-surface p-3 shadow-md animate-fade-in"
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
