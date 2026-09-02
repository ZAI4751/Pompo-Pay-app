"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { LayoutDashboard, Smartphone } from "lucide-react";
import { PompoMark } from "@/components/brand/PompoMark";
import { ThemeToggle } from "@/components/layout/ThemeToggle";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { cn } from "@/lib/utils/cn";

const links = [
  { href: "/", label: "Wallet", icon: Smartphone },
  { href: "/insights", label: "Insights", icon: LayoutDashboard },
];

export function ExperienceChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="pompo-mesh min-h-screen">
      <header className="sticky top-0 z-40 border-b border-white/50 bg-white/55 backdrop-blur-xl dark:border-white/10 dark:bg-slate-950/55">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <Link href="/" className="flex min-w-0 items-center gap-2.5">
            <PompoMark size={32} />
            <div className="min-w-0">
              <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Pompo</p>
              <p className="truncate text-sm font-semibold text-text">Pay</p>
            </div>
          </Link>
          <nav className="flex items-center gap-1 rounded-full bg-white/70 p-1 shadow-sm dark:bg-slate-900/70">
            {links.map((link) => {
              const active = pathname === link.href;
              const Icon = link.icon;
              return (
                <Link
                  key={link.href}
                  href={link.href}
                  className={cn(
                    "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-sm font-medium transition-transform duration-200 hover:scale-[1.03]",
                    active
                      ? "bg-primary text-primary-foreground shadow-sm"
                      : "text-text-muted hover:text-text",
                  )}
                >
                  <Icon className="h-4 w-4" aria-hidden="true" />
                  <span className="hidden sm:inline">{link.label}</span>
                </Link>
              );
            })}
          </nav>
          <div className="flex items-center gap-2">
            <MockDataBadge />
            <ThemeToggle />
            <Link
              href="/login"
              className="rounded-full border border-border bg-white/80 px-3 py-1.5 text-xs font-semibold text-text-muted transition hover:border-primary hover:text-text"
            >
              Admin
            </Link>
          </div>
        </div>
      </header>
      {children}
    </div>
  );
}
