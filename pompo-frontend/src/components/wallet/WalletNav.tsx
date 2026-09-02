"use client";

import { Home, UserRound, Wallet, BarChart3, ScanLine } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import type { WalletTab } from "@/lib/experience/data";

const items: { id: WalletTab; label: string; icon: typeof Home }[] = [
  { id: "home", label: "Home", icon: Home },
  { id: "assistant", label: "Wallet", icon: Wallet },
  { id: "payment", label: "Stats", icon: BarChart3 },
  { id: "profile", label: "Profile", icon: UserRound },
];

export function WalletNav({
  active,
  onChange,
  onScan,
}: {
  active: WalletTab;
  onChange: (tab: WalletTab) => void;
  onScan: () => void;
}) {
  const left = items.slice(0, 2);
  const right = items.slice(2);

  return (
    <nav className="relative mx-3 mb-3 mt-1 flex items-center justify-between rounded-[28px] bg-white/85 px-3 py-2 shadow-[0_12px_40px_-20px_rgb(15_23_42_/_0.5)] backdrop-blur-xl dark:bg-slate-900/85">
      {left.map((item) => (
        <NavBtn key={item.id} item={item} active={active} onChange={onChange} />
      ))}
      <button
        type="button"
        onClick={onScan}
        aria-label="Scan merchant QR"
        className="-mt-8 flex h-14 w-14 items-center justify-center rounded-full bg-primary text-primary-foreground shadow-[0_12px_30px_-8px_rgb(37_99_235_/_0.7)] transition-transform duration-200 hover:scale-105 active:scale-95"
      >
        <ScanLine className="h-6 w-6" />
      </button>
      {right.map((item) => (
        <NavBtn key={item.id} item={item} active={active} onChange={onChange} />
      ))}
    </nav>
  );
}

function NavBtn({
  item,
  active,
  onChange,
}: {
  item: (typeof items)[number];
  active: WalletTab;
  onChange: (tab: WalletTab) => void;
}) {
  const Icon = item.icon;
  const isActive = active === item.id;
  return (
    <button
      type="button"
      onClick={() => onChange(item.id)}
      className={cn(
        "flex min-w-[52px] flex-col items-center gap-0.5 rounded-2xl px-2 py-1 text-[10px] font-medium transition-colors",
        isActive ? "text-primary" : "text-text-subtle hover:text-text",
      )}
    >
      <Icon className="h-5 w-5" strokeWidth={isActive ? 2.4 : 1.8} />
      {item.label}
    </button>
  );
}
