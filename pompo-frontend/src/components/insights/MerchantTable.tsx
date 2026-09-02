import { MoreHorizontal, Star } from "lucide-react";
import type { MerchantRow } from "@/lib/experience/data";
import { formatWallet } from "@/lib/experience/data";
import { Skeleton } from "@/components/ui/Skeleton";

export function MerchantTable({ rows, loading }: { rows: MerchantRow[]; loading?: boolean }) {
  return (
    <article className="overflow-hidden rounded-3xl bg-white/85 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <div className="flex items-center justify-between px-5 py-4">
        <p className="text-sm font-semibold text-text">Top merchants</p>
        <MoreHorizontal className="h-4 w-4 text-text-subtle" />
      </div>
      <div className="overflow-x-auto">
        <table className="min-w-full text-left text-sm">
          <thead className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-subtle">
            <tr>
              <th className="px-5 py-2 font-semibold">ID</th>
              <th className="px-5 py-2 font-semibold">Name</th>
              <th className="px-5 py-2 font-semibold">Paid</th>
              <th className="px-5 py-2 font-semibold">Revenue</th>
              <th className="px-5 py-2 font-semibold">Rating</th>
            </tr>
          </thead>
          <tbody>
            {loading
              ? Array.from({ length: 4 }).map((_, index) => (
                  <tr key={index}>
                    <td className="px-5 py-3" colSpan={5}>
                      <Skeleton className="h-8 rounded-xl" />
                    </td>
                  </tr>
                ))
              : rows.map((row) => (
                  <tr key={row.id} className="border-t border-border/70 hover:bg-primary-light/40">
                    <td className="px-5 py-3 font-mono text-xs text-text-subtle">{row.code}</td>
                    <td className="px-5 py-3">
                      <div className="flex items-center gap-3">
                        <span className="flex h-9 w-9 items-center justify-center rounded-2xl bg-gradient-to-br from-primary/20 to-violet-200 text-xs font-bold text-primary">
                          {row.name.slice(0, 2)}
                        </span>
                        <div>
                          <p className="font-semibold text-text">{row.name}</p>
                          <p className="text-xs text-text-subtle">{row.category}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-5 py-3 text-text-muted">{row.sold}</td>
                    <td className="px-5 py-3 font-semibold tabular-nums text-emerald-600">
                      {formatWallet(row.revenue)}
                    </td>
                    <td className="px-5 py-3">
                      <span className="inline-flex items-center gap-1 font-semibold text-text">
                        <Star className="h-3.5 w-3.5 fill-amber-400 text-amber-400" />
                        {row.rating.toFixed(1)}
                      </span>
                    </td>
                  </tr>
                ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
