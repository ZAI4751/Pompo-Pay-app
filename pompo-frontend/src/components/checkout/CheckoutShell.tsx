import type { ReactNode } from "react";
import Image from "next/image";
import { Lock } from "lucide-react";
import { PUBLIC_CHECKOUT_ORIGIN } from "@/lib/checkout/publicCheckout";

export function CheckoutShell({ children }: { children: ReactNode }) {
  return (
    <div className="checkout-root min-h-dvh text-text flex flex-col">
      <div className="pompo-aurora pointer-events-none absolute inset-0" aria-hidden="true" />
      <header className="sticky top-0 z-30 border-b border-border bg-surface/90 backdrop-blur-md">
        <div className="mx-auto flex h-14 max-w-md items-center justify-between px-4">
          <div className="flex min-w-0 items-center gap-2.5">
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
              <p className="truncate text-[11px] text-text-subtle">Secure payment</p>
            </div>
          </div>
          <div className="flex shrink-0 items-center gap-1.5 text-[11px] text-text-subtle">
            <Lock className="h-3.5 w-3.5 text-success" aria-hidden="true" />
            <span className="hidden xs:inline sm:inline">pay.pompo.mw</span>
          </div>
        </div>
      </header>

      <main className="relative mx-auto flex w-full max-w-md flex-1 flex-col px-4 pb-[max(1.5rem,env(safe-area-inset-bottom))] pt-5">
        {children}
      </main>

      <footer className="relative px-4 py-4 text-center text-[11px] leading-relaxed text-text-subtle">
        You are paying through {PUBLIC_CHECKOUT_ORIGIN.replace("https://", "")}. POMPO never
        asks for card numbers, CVV, or provider PINs on this page.
      </footer>
    </div>
  );
}

export function CheckoutStatusCard({
  tone,
  icon,
  title,
  children,
}: {
  tone: "neutral" | "success" | "warning" | "error" | "info";
  icon: ReactNode;
  title: string;
  children: ReactNode;
}) {
  const tones = {
    neutral: "border-border bg-surface",
    success: "border-success/30 bg-success-bg",
    warning: "border-warning/30 bg-warning-bg",
    error: "border-error/30 bg-error-bg",
    info: "border-info/25 bg-info-bg",
  };

  return (
    <section className={`card-depth my-auto rounded-2xl border p-6 text-center ${tones[tone]}`}>
      <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-surface text-text">
        {icon}
      </div>
      <h1 className="text-xl font-semibold tracking-tight text-text">{title}</h1>
      <div className="mt-2 text-sm leading-relaxed text-text-muted">{children}</div>
    </section>
  );
}
