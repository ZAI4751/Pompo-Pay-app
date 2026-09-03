"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function TransactionsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/payments");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center text-sm text-text-muted">
      Redirecting to Payments…
    </div>
  );
}
