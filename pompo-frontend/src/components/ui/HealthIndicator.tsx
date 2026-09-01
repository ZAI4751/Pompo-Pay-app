import { cn } from "@/lib/utils/cn";

type HealthKind = "active" | "degraded" | "pending" | "processing" | "unavailable" | "idle";

const labels: Record<HealthKind, string> = {
  active: "Active",
  degraded: "Degraded",
  pending: "Pending",
  processing: "Processing",
  unavailable: "Unavailable",
  idle: "Idle",
};

const live: Record<HealthKind, boolean> = {
  active: true,
  degraded: true,
  pending: true,
  processing: true,
  unavailable: false,
  idle: false,
};

export function HealthIndicator({
  state,
  label,
  className,
}: {
  state: HealthKind;
  label?: string;
  className?: string;
}) {
  const pulsing = live[state];
  return (
    <span className={cn("inline-flex shrink-0 items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wide", className)}>
      <span className="relative flex h-2 w-2" aria-hidden="true">
        {pulsing && (
          <span
            className={cn(
              "absolute inset-0 rounded-full opacity-60 motion-safe:animate-ping",
              state === "active" && "bg-success",
              state === "degraded" && "bg-warning",
              (state === "pending" || state === "processing") && "bg-info",
            )}
          />
        )}
        <span
          className={cn(
            "relative h-2 w-2 rounded-full",
            state === "active" && "bg-success motion-safe:animate-pulse-dot",
            state === "degraded" && "bg-warning motion-safe:animate-pulse-dot",
            state === "pending" && "bg-warning motion-safe:animate-pulse-dot",
            state === "processing" && "bg-info motion-safe:animate-pulse-dot",
            state === "unavailable" && "bg-error",
            state === "idle" && "bg-text-subtle",
          )}
        />
      </span>
      {label ?? labels[state]}
    </span>
  );
}
