import { ArrowDownRight, ArrowUpRight, Eye, Inbox, MousePointer2, Users } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { Kpi } from "@/lib/experience/data";
import { Skeleton } from "@/components/ui/Skeleton";

const icons = {
  eye: Eye,
  users: Users,
  pointer: MousePointer2,
  inbox: Inbox,
};

export function KpiCard({ kpi, loading }: { kpi: Kpi; loading?: boolean }) {
  const Icon = icons[kpi.icon];
  const up = kpi.delta >= 0;
  return (
    <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <div className="flex items-start justify-between">
        <p className="text-sm text-text-muted">{kpi.label}</p>
        <span className="rounded-2xl bg-primary-light p-2 text-primary">
          <Icon className="h-4 w-4" />
        </span>
      </div>
      {loading ? (
        <Skeleton className="mt-3 h-8 w-24" />
      ) : (
        <p className="mt-3 text-3xl font-semibold tabular-nums text-text">{kpi.value}</p>
      )}
      <p className={cn("mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-semibold", up ? "bg-emerald-50 text-emerald-700" : "bg-rose-50 text-rose-700")}>
        {up ? <ArrowUpRight className="h-3.5 w-3.5" /> : <ArrowDownRight className="h-3.5 w-3.5" />}
        {up ? "+" : ""}
        {kpi.delta}% vs. last period
      </p>
    </article>
  );
}
