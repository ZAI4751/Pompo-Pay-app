"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function SecurityRedirectPage() {
  const router = useRouter();

  useEffect(() => {
    router.replace("/settings/security");
  }, [router]);

  return (
    <div className="flex h-full items-center justify-center text-sm text-text-muted">
      Redirecting to Settings → Security…
    </div>
  );
}
