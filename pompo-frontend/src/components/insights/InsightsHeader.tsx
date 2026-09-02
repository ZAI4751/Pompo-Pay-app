"use client";

import { useEffect, useState } from "react";
import { Bell, Calendar, Command, Download, Menu, PlusSquare, Search } from "lucide-react";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { cn } from "@/lib/utils/cn";

export function InsightsHeader({
  period,
  onPeriod,
  onMenu,
  onExport,
}: {
  period: "7d" | "30d";
  onPeriod: (value: "7d" | "30d") => void;
  onMenu: () => void;
  onExport: () => void;
}) {
  const [query, setQuery] = useState("");
  const [palette, setPalette] = useState(false);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setPalette(true);
      }
      if (event.key === "Escape") setPalette(false);
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-2xl bg-white shadow-sm lg:hidden"
          aria-label="Open navigation"
          onClick={onMenu}
        >
          <Menu className="h-5 w-5" />
        </button>
        <label className="relative min-w-0 flex-1">
          <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-text-subtle" />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            onFocus={() => setPalette(true)}
            placeholder="Search anything..."
            className="h-11 w-full rounded-full border border-transparent bg-white/80 pl-10 pr-16 text-sm text-text shadow-sm outline-none placeholder:text-text-subtle focus:border-primary dark:bg-slate-900/70"
          />
          <span className="absolute right-3 top-1/2 hidden -translate-y-1/2 items-center gap-0.5 rounded-md border border-border px-1.5 py-0.5 text-[10px] font-semibold text-text-subtle sm:inline-flex">
            <Command className="h-3 w-3" />K
          </span>
        </label>
        <MockDataBadge />
        <ThemeToggle />
        <button type="button" aria-label="Notifications" className="relative rounded-full bg-white p-2.5 shadow-sm dark:bg-slate-900">
          <Bell className="h-4 w-4 text-text-muted" />
          <span className="absolute right-2 top-2 h-2 w-2 rounded-full bg-rose-500" />
        </button>
        <div className="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet-400 text-xs font-bold text-white">
          GP
        </div>
      </div>

      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <h1 className="text-3xl font-semibold tracking-tight text-text">Dashboard</h1>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-sm text-text-muted shadow-sm dark:bg-slate-900">
            <Calendar className="h-4 w-4" />
            Jan 1, 2025 – Feb 1, 2025
          </span>
          <div className="flex rounded-full bg-white p-1 shadow-sm dark:bg-slate-900">
            {(["7d", "30d"] as const).map((item) => (
              <button
                key={item}
                type="button"
                onClick={() => onPeriod(item)}
                className={cn(
                  "rounded-full px-3 py-1.5 text-sm font-medium",
                  period === item ? "bg-primary text-primary-foreground" : "text-text-muted",
                )}
              >
                {item === "7d" ? "Last 7 days" : "Last 30 days"}
              </button>
            ))}
          </div>
          <button type="button" className="inline-flex items-center gap-1.5 rounded-full bg-white px-3 py-2 text-sm font-medium text-text shadow-sm hover:scale-105 dark:bg-slate-900">
            <PlusSquare className="h-4 w-4" />
            Add widget
          </button>
          <button
            type="button"
            onClick={onExport}
            className="inline-flex items-center gap-1.5 rounded-full bg-primary px-3 py-2 text-sm font-semibold text-primary-foreground shadow-sm hover:bg-primary-hover"
          >
            <Download className="h-4 w-4" />
            Export
          </button>
        </div>
      </div>

      {palette ? (
        <div className="rounded-3xl border border-border bg-white p-3 text-sm text-text-muted shadow-lg dark:bg-slate-900">
          Searching “{query || "payments, merchants, QR"}”. Command palette is visual-only in this preview.
          <button type="button" className="ml-3 font-semibold text-primary" onClick={() => setPalette(false)}>
            Close
          </button>
        </div>
      ) : null}
    </div>
  );
}
