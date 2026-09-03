"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function ExceptionsRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/reconciliation");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center text-sm text-text-muted">
      Redirecting to Reconciliation…
    </div>
  );
}
