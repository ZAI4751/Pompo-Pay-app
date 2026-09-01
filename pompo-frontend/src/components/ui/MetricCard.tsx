"use client";

import type { LucideIcon } from "lucide-react";
import { m } from "framer-motion";
import { Sparkline } from "@/components/charts/Sparkline";
import { AnimatedNumber } from "@/components/motion/AnimatedNumber";
import { cn } from "@/lib/utils/cn";
import { cardHover, cardTransition } from "@/lib/motion";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trend?: { value: string; positive: boolean };
  hint?: string;
  series?: number[];
  emphasis?: "primary" | "secondary";
  numericValue?: number;
  formatNumeric?: (value: number) => string;
}

export function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  hint,
  series,
  emphasis = "secondary",
  numericValue,
  formatNumeric,
}: MetricCardProps) {
  const primary = emphasis === "primary";
  return (
    <m.div
      whileHover={cardHover}
      transition={cardTransition}
      className={cn(
        "h-full min-w-0 rounded-md border px-4 py-4 card-depth transition-colors duration-200",
        primary
          ? "border-primary/30 bg-gradient-to-br from-primary-light to-white glow-ring dark:from-primary-light dark:to-slate-900/80 dark:shadow-luminous"
          : "border-border bg-white hover:border-primary/25 hover:shadow-glow dark:border-neutral-800 dark:bg-slate-900/80 dark:hover:shadow-luminous",
      )}
    >
      <div className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <p className="truncate text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
            {label}
          </p>
          <p
            className={cn(
              "mt-1.5 truncate font-semibold tabular-nums tracking-tight text-text",
              primary ? "text-3xl" : "text-2xl",
            )}
          >
            {numericValue !== undefined ? (
              <AnimatedNumber value={numericValue} format={formatNumeric} />
            ) : (
              value
            )}
          </p>
        </div>
        <div
          className={cn(
            "flex h-8 w-8 shrink-0 items-center justify-center rounded-sm",
            primary ? "bg-primary text-primary-foreground" : "bg-primary-light text-primary",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-3 flex items-end justify-between gap-4">
        {trend ? (
          <p className={cn("truncate text-xs font-medium", trend.positive ? "text-success" : "text-error")}>
            {trend.positive ? "+" : ""}
            {trend.value}
          </p>
        ) : (
          <span />
        )}
        {series && series.length > 1 && (
          <Sparkline values={series} className="h-8 w-24 shrink-0 text-primary" />
        )}
      </div>
      {hint && <p className="mt-2 truncate text-[11px] text-text-subtle">{hint}</p>}
    </m.div>
  );
}
