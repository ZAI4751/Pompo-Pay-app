import type { Metadata } from "next";
import { Suspense } from "react";
import { AccountShell } from "@/components/account/AccountShell";

export const metadata: Metadata = {
  title: "POMPO account",
  description: "Manage your POMPO customer account, activity, and security.",
};

export default function AccountLayout({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={<div className="checkout-root min-h-dvh" />}>
      <AccountShell>{children}</AccountShell>
    </Suspense>
  );
}
