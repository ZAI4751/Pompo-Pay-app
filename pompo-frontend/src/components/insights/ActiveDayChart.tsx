"use client";

import { useState } from "react";
import { cn } from "@/lib/utils/cn";

export function ActiveDayChart({
  days,
}: {
  days: { day: string; value: number }[];
}) {
  const max = Math.max(...days.map((item) => item.value), 1);
  const peak = days[0]
    ? days.reduce((best, item) => (item.value > best.value ? item : best), days[0])
    : undefined;
  const [hover, setHover] = useState<string | null>(peak?.day ?? null);

  return (
    <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <p className="text-sm font-semibold text-text">Most active day</p>
      <div className="mt-6 flex h-44 items-end justify-between gap-2">
        {days.length === 0 ? (
          <p className="w-full self-center text-center text-sm text-text-muted">No activity yet.</p>
        ) : null}
        {days.map((item) => {
          const active = (hover ?? peak?.day) === item.day;
          const height = Math.max(12, (item.value / max) * 100);
          return (
            <button
              key={item.day}
              type="button"
              onMouseEnter={() => setHover(item.day)}
              onFocus={() => setHover(item.day)}
              className="flex h-full flex-1 flex-col items-center justify-end gap-2"
            >
              {active ? (
                <span className="rounded-full bg-primary px-2 py-0.5 text-[10px] font-semibold text-white">
                  {item.value.toLocaleString("en-MW")}
                </span>
              ) : (
                <span className="h-4" />
              )}
              <span
                className={cn(
                  "w-full max-w-[28px] rounded-full transition-all",
                  active ? "bg-primary" : "bg-slate-200 dark:bg-slate-700",
                )}
                style={{ height: `${height}%` }}
              />
              <span className={cn("text-xs", active ? "font-semibold text-primary" : "text-text-subtle")}>
                {item.day}
              </span>
            </button>
          );
        })}
      </div>
    </article>
  );
}
