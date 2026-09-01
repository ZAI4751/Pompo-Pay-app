import { cn } from "@/lib/utils/cn";

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("skeleton rounded", className)} aria-hidden="true" />;
}

export function TableSkeleton({ rows = 5, cols = 5 }: { rows?: number; cols?: number }) {
  return (
    <div
      className="rounded-md border border-border bg-surface p-4"
      role="status"
      aria-label="Loading"
    >
      <div className="mb-3 flex gap-4">
        {Array.from({ length: cols }).map((_, c) => (
          <Skeleton key={`h-${c}`} className="h-3 flex-1" />
        ))}
      </div>
      <div className="space-y-3">
        {Array.from({ length: rows }).map((_, r) => (
          <div key={r} className="flex gap-4">
            {Array.from({ length: cols }).map((_, c) => (
              <Skeleton key={c} className="h-4 flex-1" />
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
