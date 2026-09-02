"use client";

import { useState } from "react";
import Link from "next/link";
import {
  BarChart3,
  ChevronDown,
  CircleHelp,
  CreditCard,
  LayoutDashboard,
  QrCode,
  Receipt,
  Settings,
  Store,
  Tag,
  Users,
  Wallet,
} from "lucide-react";
import { PompoMark } from "@/components/brand/PompoMark";
import { cn } from "@/lib/utils/cn";

const primary = [
  { href: "/insights", label: "Dashboard", icon: LayoutDashboard, active: true },
  { href: "/insights", label: "Payments", icon: CreditCard, badge: "46" },
  { href: "/insights", label: "Merchants", icon: Store },
  { href: "/insights", label: "Payers", icon: Users },
  { href: "/insights", label: "QR codes", icon: QrCode },
];

const finance = [
  { label: "Settlements", icon: Wallet },
  { label: "Transactions", icon: Receipt },
  { label: "Reports", icon: BarChart3 },
];

export function InsightsSidebar({
  open,
  onNavigate,
}: {
  open: boolean;
  onNavigate?: () => void;
}) {
  const [financesOpen, setFinancesOpen] = useState(true);

  return (
    <aside
      className={cn(
        "flex h-full w-[260px] shrink-0 flex-col border-r border-border bg-white/80 p-4 backdrop-blur-xl dark:bg-slate-950/70",
        "max-lg:fixed max-lg:inset-y-0 max-lg:left-0 max-lg:z-40 max-lg:shadow-2xl",
        open ? "max-lg:translate-x-0" : "max-lg:-translate-x-full",
        "transition-transform duration-200",
      )}
    >
      <Link href="/" className="mb-6 flex items-center gap-2.5 px-1" onClick={onNavigate}>
        <PompoMark size={30} />
        <span className="text-lg font-semibold text-text">Pompo</span>
      </Link>
      <nav className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto scrollbar-thin">
        {primary.map((item) => {
          const Icon = item.icon;
          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={onNavigate}
              className={cn(
                "flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium transition-colors",
                item.active
                  ? "bg-primary-light text-primary"
                  : "text-text-muted hover:bg-surface-raised hover:text-text",
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="flex-1">{item.label}</span>
              {item.badge ? (
                <span className="rounded-full bg-emerald-500 px-1.5 py-0.5 text-[10px] font-bold text-white">
                  {item.badge}
                </span>
              ) : null}
            </Link>
          );
        })}
        <button
          type="button"
          onClick={() => setFinancesOpen((value) => !value)}
          className="mt-3 flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm font-medium text-text-muted hover:bg-surface-raised hover:text-text"
        >
          <Wallet className="h-4 w-4" />
          <span className="flex-1 text-left">Finances</span>
          <ChevronDown className={cn("h-4 w-4 transition", financesOpen && "rotate-180")} />
        </button>
        {financesOpen
          ? finance.map((item) => {
              const Icon = item.icon;
              return (
                <span
                  key={item.label}
                  className="flex items-center gap-3 rounded-2xl px-3 py-2 pl-10 text-sm text-text-muted"
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </span>
              );
            })
          : null}
        <span className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm text-text-muted">
          <BarChart3 className="h-4 w-4" />
          Analytics
        </span>
        <span className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm text-text-muted">
          <Tag className="h-4 w-4" />
          Promos
        </span>
      </nav>
      <div className="mt-4 space-y-1">
        <span className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm text-text-muted">
          <Settings className="h-4 w-4" />
          Settings
        </span>
        <span className="flex items-center gap-3 rounded-2xl px-3 py-2.5 text-sm text-text-muted">
          <CircleHelp className="h-4 w-4" />
          Help & Support
        </span>
      </div>
      <div className="mt-4 rounded-3xl bg-gradient-to-br from-dark-blue to-primary p-4 text-white">
        <p className="text-sm font-semibold">Go live with rails</p>
        <p className="mt-1 text-xs text-white/75">Connect Airtel, TNM, or bank payouts when contracts are ready.</p>
        <Link
          href="/login"
          className="mt-3 inline-flex rounded-full bg-white px-3 py-1.5 text-xs font-semibold text-dark-blue transition hover:scale-105"
        >
          Open Master Admin
        </Link>
      </div>
    </aside>
  );
}
