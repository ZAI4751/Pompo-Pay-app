import { Building2, MoreHorizontal, Smartphone, Store } from "lucide-react";
import { cn } from "@/lib/utils/cn";

const tones = {
  blue: { icon: "bg-blue-50 text-blue-600", bar: "bg-blue-500" },
  green: { icon: "bg-emerald-50 text-emerald-600", bar: "bg-emerald-500" },
  orange: { icon: "bg-orange-50 text-orange-600", bar: "bg-orange-500" },
};

const icons = {
  airtel: Smartphone,
  tnm: Store,
  bank: Building2,
};

export function SegmentStrip({
  title,
  items,
}: {
  title: string;
  items: { id: string; label: string; value: string; share: number; tone: "blue" | "green" | "orange" }[];
}) {
  return (
    <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <div className="mb-4 flex items-center justify-between">
        <p className="text-sm font-semibold text-text">{title}</p>
        <MoreHorizontal className="h-4 w-4 text-text-subtle" />
      </div>
      <div className="grid gap-4 sm:grid-cols-3">
        {items.map((item) => {
          const Icon = icons[item.id as keyof typeof icons] ?? Store;
          const tone = tones[item.tone];
          return (
            <div key={item.id}>
              <div className="flex items-center gap-2">
                <span className={cn("rounded-xl p-2", tone.icon)}>
                  <Icon className="h-4 w-4" />
                </span>
                <div>
                  <p className="text-xl font-semibold tabular-nums text-text">{item.value}</p>
                  <p className="text-xs text-text-muted">{item.label}</p>
                </div>
              </div>
              <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100 dark:bg-slate-800">
                <div className={cn("h-full rounded-full", tone.bar)} style={{ width: `${item.share}%` }} />
              </div>
            </div>
          );
        })}
      </div>
    </article>
  );
}
