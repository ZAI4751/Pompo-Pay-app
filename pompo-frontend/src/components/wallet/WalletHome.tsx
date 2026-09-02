"use client";

import { ArrowDownLeft, ArrowUpRight, ArrowLeftRight, Coins, CreditCard, Eye, EyeOff, Plus } from "lucide-react";
import { PompoMark } from "@/components/brand/PompoMark";
import { TransactionRow } from "./TransactionRow";
import { formatWallet } from "@/lib/experience/data";
import type { WalletTxn } from "@/lib/experience/data";
import { Skeleton } from "@/components/ui/Skeleton";

export function WalletHome({
  balance,
  hidden,
  onToggle,
  txns,
  loading,
  onSeeMore,
  onSend,
  onRequest,
}: {
  balance: number;
  hidden: boolean;
  onToggle: () => void;
  txns: WalletTxn[];
  loading: boolean;
  onSeeMore: () => void;
  onSend: () => void;
  onRequest: () => void;
}) {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-2 pt-4 scrollbar-thin">
      <div className="mb-5 flex items-center justify-center gap-2">
        <PompoMark size={22} />
        <h1 className="text-lg font-semibold tracking-tight text-text">Pompo</h1>
      </div>

      <p className="text-center text-sm text-text-muted">Wallet Balance</p>
      {loading ? (
        <Skeleton className="mx-auto mt-2 h-10 w-48 rounded-xl" />
      ) : (
        <div className="mt-1 flex items-center justify-center gap-2">
          <p className="text-[34px] font-bold leading-none tracking-tight text-text tabular-nums">
            {hidden ? "••••••••" : formatWallet(balance)}
          </p>
          <button
            type="button"
            onClick={onToggle}
            aria-label={hidden ? "Show balance" : "Hide balance"}
            className="rounded-full p-1 text-text-subtle transition hover:bg-white/70 hover:text-text"
          >
            {hidden ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
          </button>
        </div>
      )}

      <div className="mt-6 grid grid-cols-2 gap-3">
        <PillButton icon={ArrowUpRight} label="Send" onClick={onSend} />
        <PillButton icon={ArrowDownLeft} label="Request" onClick={onRequest} />
      </div>

      <div className="mt-4 flex items-center justify-between rounded-full bg-violet-100/80 px-4 py-2.5 dark:bg-violet-500/15">
        <div className="flex items-center gap-2 text-sm font-medium text-text">
          <Coins className="h-4 w-4 text-violet-600" />
          New promo!
        </div>
        <button
          type="button"
          className="rounded-full bg-white px-3 py-1 text-xs font-semibold text-text shadow-sm transition hover:scale-105"
        >
          Get Promo
        </button>
      </div>

      <Section title="Quick Actions" onMore={onSeeMore}>
        <div className="grid grid-cols-3 gap-3">
          <QuickAction icon={ArrowLeftRight} label="Transfer" tint="from-violet-200 to-blue-100" />
          <QuickAction icon={Plus} label="Top Up" tint="from-orange-200 to-amber-100" />
          <QuickAction icon={CreditCard} label="Payment" tint="from-teal-200 to-emerald-100" onClick={onSeeMore} />
        </div>
      </Section>

      <Section title="Transactions" onMore={onSeeMore}>
        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-14 rounded-2xl" />
            <Skeleton className="h-14 rounded-2xl" />
          </div>
        ) : (
          txns.slice(0, 3).map((txn) => <TransactionRow key={txn.id} txn={txn} />)
        )}
      </Section>
    </div>
  );
}

function PillButton({
  icon: Icon,
  label,
  onClick,
}: {
  icon: typeof ArrowUpRight;
  label: string;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex items-center justify-center gap-2 rounded-full bg-white py-3 text-sm font-semibold text-text shadow-[0_8px_24px_-16px_rgb(15_23_42_/_0.5)] transition-transform duration-200 hover:scale-[1.03] active:scale-[0.98] dark:bg-slate-900/80"
    >
      <Icon className="h-4 w-4" />
      {label}
    </button>
  );
}

function QuickAction({
  icon: Icon,
  label,
  tint,
  onClick,
}: {
  icon: typeof CreditCard;
  label: string;
  tint: string;
  onClick?: () => void;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex flex-col items-center gap-2 rounded-3xl bg-white/80 px-2 py-4 shadow-sm transition-transform hover:scale-[1.04] dark:bg-slate-900/70"
    >
      <span className={`flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br ${tint}`}>
        <Icon className="h-5 w-5 text-text" />
      </span>
      <span className="text-xs font-medium text-text">{label}</span>
    </button>
  );
}

function Section({
  title,
  onMore,
  children,
}: {
  title: string;
  onMore: () => void;
  children: React.ReactNode;
}) {
  return (
    <section className="mt-6">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-base font-semibold text-text">{title}</h2>
        <button type="button" onClick={onMore} className="text-xs font-semibold text-primary hover:underline">
          See More
        </button>
      </div>
      {children}
    </section>
  );
}
