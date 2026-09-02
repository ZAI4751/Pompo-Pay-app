"use client";

import { useState } from "react";
import { ArrowLeft, MoreHorizontal } from "lucide-react";
import { DonutChart } from "./DonutChart";
import { TransactionRow } from "./TransactionRow";
import { formatWallet } from "@/lib/experience/data";
import { expenseTotal, incomeTotal, type BillCard, type WalletTxn } from "@/lib/experience/data";
import { cn } from "@/lib/utils/cn";

export function WalletPayment({
  bills,
  txns,
  onBack,
}: {
  bills: BillCard[];
  txns: WalletTxn[];
  onBack: () => void;
}) {
  const [index, setIndex] = useState(0);
  const bill = bills[index] ?? bills[0];

  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-2 pt-3 scrollbar-thin">
      <div className="mb-4 grid grid-cols-[2rem_1fr_2rem] items-center">
        <button type="button" onClick={onBack} aria-label="Back" className="rounded-full p-1 hover:bg-white/60">
          <ArrowLeft className="h-5 w-5 text-text" />
        </button>
        <h1 className="text-center text-lg font-semibold text-text">Payment</h1>
        <button type="button" aria-label="More" className="justify-self-end rounded-full p-1 hover:bg-white/60">
          <MoreHorizontal className="h-5 w-5 text-text" />
        </button>
      </div>

      {bill ? (
        <article className="relative overflow-hidden rounded-[28px] bg-gradient-to-br from-orange-400 via-rose-400 to-fuchsia-500 p-5 text-white shadow-lg">
          <div
            className="pointer-events-none absolute inset-0 opacity-30"
            style={{
              backgroundImage:
                "radial-gradient(circle at 20% 20%, white 0 1px, transparent 1.5px), radial-gradient(circle at 80% 70%, white 0 1px, transparent 1.5px)",
              backgroundSize: "24px 24px",
            }}
          />
          <div className="relative">
            <div className="flex items-start justify-between">
              <p className="text-sm font-medium text-white/90">{bill.title}</p>
              <span className="rounded-full bg-white/20 px-2.5 py-1 text-[11px] font-semibold backdrop-blur">
                {bill.dueLabel}
              </span>
            </div>
            <p className="mt-6 font-mono text-sm tracking-[0.18em] text-white/85">{bill.masked}</p>
            <p className="mt-6 text-xs text-white/75">Amount Due</p>
            <p className="text-3xl font-bold tabular-nums">{formatWallet(bill.amount)}</p>
          </div>
        </article>
      ) : null}

      <div className="mt-3 flex justify-center gap-1.5">
        {bills.map((item, i) => (
          <button
            key={item.id}
            type="button"
            aria-label={`Show ${item.title}`}
            onClick={() => setIndex(i)}
            className={cn(
              "h-2 rounded-full transition-all",
              i === index ? "w-5 bg-primary" : "w-2 bg-white/80 hover:bg-primary/40",
            )}
          />
        ))}
      </div>

      <h2 className="mb-3 mt-6 text-base font-semibold text-text">Statistic</h2>
      <div className="rounded-[28px] bg-white/80 p-4 shadow-sm dark:bg-slate-900/70">
        <DonutChart income={incomeTotal} expense={expenseTotal} />
      </div>

      <h2 className="mb-2 mt-6 text-base font-semibold text-text">History</h2>
      {txns.map((txn) => (
        <TransactionRow key={txn.id} txn={txn} />
      ))}
    </div>
  );
}
