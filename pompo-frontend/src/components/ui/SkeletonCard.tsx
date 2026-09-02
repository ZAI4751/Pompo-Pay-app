import { Skeleton } from "./Skeleton";
import { cn } from "@/lib/utils/cn";

export function SkeletonCard({ className, lines = 3 }: { className?: string; lines?: number }) {
  return (
    <div
      className={cn("rounded-2xl border border-border bg-surface p-4 card-depth", className)}
      role="status"
      aria-label="Loading"
    >
      <Skeleton className="h-3 w-24" />
      <Skeleton className="mt-3 h-8 w-32" />
      <div className="mt-4 space-y-2">
        {Array.from({ length: lines }).map((_, index) => (
          <Skeleton key={index} className="h-3 w-full" />
        ))}
      </div>
    </div>
  );
}

export function MetricSkeleton() {
  return (
    <div className="rounded-2xl border border-border bg-surface px-5 py-5 card-depth" role="status" aria-label="Loading metric">
      <div className="flex items-start justify-between">
        <Skeleton className="h-3 w-28" />
        <Skeleton className="h-8 w-8 rounded-sm" />
      </div>
      <Skeleton className="mt-3 h-8 w-24" />
      <Skeleton className="mt-4 h-8 w-full" />
    </div>
  );
}
