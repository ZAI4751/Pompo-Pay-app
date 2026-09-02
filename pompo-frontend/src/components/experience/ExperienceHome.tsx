"use client";

import { WalletApp } from "@/components/wallet/WalletApp";

export function ExperienceHome() {
  return (
    <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
      <div className="mx-auto max-w-2xl text-center">
        <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Customer wallet</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-text sm:text-4xl">
          Send, request, and pay — with a scan in the middle.
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-text-muted sm:text-base">
          Interactive preview of the Pompo wallet. Money movement stays in the mobile app and the
          API; this screen is the visual system for home, assistant, and payments.
        </p>
      </div>

      <div className="mt-10 hidden items-start justify-center gap-6 xl:flex">
        <WalletApp lockedTab="home" />
        <WalletApp lockedTab="assistant" />
        <WalletApp lockedTab="payment" />
      </div>

      <div className="mt-8 xl:hidden">
        <WalletApp />
      </div>
    </main>
  );
}
