"use client";

import Link from "next/link";
import Image from "next/image";
import { usePathname, useSearchParams } from "next/navigation";
import { Lock } from "lucide-react";
import { useCustomerSession } from "@/lib/customer/CustomerSessionProvider";
import { ACCOUNT_NAV } from "@/lib/customer/customerAccount";
import { PUBLIC_CHECKOUT_ORIGIN } from "@/lib/checkout/publicCheckout";
import { CustomerAuthCard } from "@/components/account/CustomerAuthCard";

export function AccountShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const { user, status, signOut } = useCustomerSession();
  const from = searchParams.get("from");
  const checkoutReturn = from?.startsWith("/p/") ? from : null;

  return (
    <div className="checkout-root min-h-dvh text-text flex flex-col">
      <div className="pompo-aurora pointer-events-none absolute inset-0" aria-hidden="true" />
      <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-md items-center justify-between px-4">
          <Link href={checkoutReturn || "/account"} className="flex min-w-0 items-center gap-2.5">
            <Image
              src="/pompo-mark.png"
              alt=""
              width={32}
              height={32}
              priority
              unoptimized
              className="h-8 w-8 shrink-0 rounded-lg"
            />
            <div className="min-w-0">
              <p className="text-[15px] font-semibold tracking-tight text-text">POMPO</p>
              <p className="truncate text-[11px] text-text-subtle">Pay with POMPO</p>
            </div>
          </Link>
          <div className="flex shrink-0 items-center gap-1.5 text-[11px] text-text-subtle">
            <Lock className="h-3.5 w-3.5 text-success" aria-hidden="true" />
            <span>Account</span>
          </div>
        </div>
      </header>

      <main className="relative mx-auto flex w-full max-w-md flex-1 flex-col px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-5">
        {status === "loading" ? (
          <p className="my-auto text-center text-sm text-text-muted">Loading your account…</p>
        ) : status !== "authenticated" || !user ? (
          <CustomerAuthCard returnTo={checkoutReturn || pathname || "/account"} />
        ) : (
          <>
            {checkoutReturn ? (
              <Link href={checkoutReturn} className="mb-3 text-xs font-semibold text-primary">
                Back to payment
              </Link>
            ) : null}
            <nav className="-mx-1 mb-4 flex gap-1 overflow-x-auto pb-1" aria-label="Account">
              {ACCOUNT_NAV.map((item) => {
                const active = item.href === "/account" ? pathname === "/account" : pathname.startsWith(item.href);
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={`shrink-0 rounded-full px-3 py-1.5 text-xs font-semibold ${
                      active ? "bg-primary text-primary-foreground" : "bg-surface-inset text-text-muted"
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
            {children}
            <button
              type="button"
              onClick={() => void signOut()}
              className="mt-8 w-full rounded-xl border border-border py-3 text-sm font-semibold text-text"
            >
              Sign out
            </button>
          </>
        )}
      </main>

      <footer className="relative px-4 py-4 text-center text-[11px] leading-relaxed text-text-subtle">
        You are using {PUBLIC_CHECKOUT_ORIGIN.replace("https://", "")}. The POMPO app remains the
        full customer experience.
      </footer>
    </div>
  );
}
