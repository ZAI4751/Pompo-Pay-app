import type { LucideIcon } from "lucide-react";
import { Sparkline } from "@/components/charts/Sparkline";
import { cn } from "@/lib/utils/cn";

interface MetricCardProps {
  label: string;
  value: string;
  icon: LucideIcon;
  trend?: { value: string; positive: boolean };
  hint?: string;
  series?: number[];
  emphasis?: "primary" | "secondary";
}

export function MetricCard({
  label,
  value,
  icon: Icon,
  trend,
  hint,
  series,
  emphasis = "secondary",
}: MetricCardProps) {
  const primary = emphasis === "primary";
  return (
    <div
      className={cn(
        "rounded-md border px-4 py-4 transition-colors duration-150 card-depth",
        primary
          ? "border-primary/30 bg-primary-light glow-ring"
          : "border-border bg-surface hover:border-primary/25",
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
            {label}
          </p>
          <p
            className={cn(
              "mt-1.5 font-semibold tabular-nums tracking-tight text-text",
              primary ? "text-3xl" : "text-2xl",
            )}
          >
            {value}
          </p>
        </div>
        <div
          className={cn(
            "rounded-sm p-2",
            primary ? "bg-primary text-primary-foreground" : "bg-primary-light text-primary",
          )}
        >
          <Icon className="h-4 w-4" aria-hidden="true" />
        </div>
      </div>
      <div className="mt-3 flex items-end justify-between gap-3">
        {trend ? (
          <p className={cn("text-xs font-medium", trend.positive ? "text-success" : "text-error")}>
            {trend.positive ? "+" : ""}
            {trend.value}
          </p>
        ) : (
          <span />
        )}
        {series && series.length > 1 && (
          <Sparkline values={series} className="h-8 w-24 text-primary" />
        )}
      </div>
      {hint && <p className="mt-2 text-[11px] text-text-subtle">{hint}</p>}
    </div>
  );
}
