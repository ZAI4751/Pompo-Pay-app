import { cn } from "@/lib/utils/cn";
import type { WalletTxn } from "@/lib/experience/data";
import { formatWallet } from "@/lib/experience/data";

const tone: Record<WalletTxn["tone"], string> = {
  violet: "bg-violet-100 text-violet-700 dark:bg-violet-500/20 dark:text-violet-200",
  orange: "bg-orange-100 text-orange-700 dark:bg-orange-500/20 dark:text-orange-200",
  teal: "bg-teal-100 text-teal-700 dark:bg-teal-500/20 dark:text-teal-200",
  rose: "bg-rose-100 text-rose-700 dark:bg-rose-500/20 dark:text-rose-200",
  slate: "bg-slate-100 text-slate-700 dark:bg-slate-500/20 dark:text-slate-200",
};

export function TransactionRow({ txn }: { txn: WalletTxn }) {
  const inflow = txn.amount > 0;
  return (
    <div className="flex items-center gap-3 rounded-2xl px-1 py-2 transition-colors hover:bg-white/60 dark:hover:bg-white/5">
      <div
        className={cn(
          "flex h-11 w-11 shrink-0 items-center justify-center rounded-full text-xs font-bold",
          tone[txn.tone],
        )}
      >
        {txn.initials}
      </div>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-semibold text-text">{txn.name}</p>
        <p className="text-xs text-text-subtle">{txn.date}</p>
      </div>
      <div className="text-right">
        <p className={cn("text-sm font-semibold tabular-nums", inflow ? "text-teal-600" : "text-text")}>
          {inflow ? "+" : ""}
          {formatWallet(txn.amount)}
        </p>
        <p className="text-[11px] text-text-subtle">{txn.kind}</p>
      </div>
    </div>
  );
}
