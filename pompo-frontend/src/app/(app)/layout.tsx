"use client";

/**
 * Route-group layout for every authenticated screen. Handles the
 * loading/unauthenticated states itself so individual pages never need to
 * -- they can assume `user` exists once rendered.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Loader2 } from "lucide-react";
import { Sidebar } from "@/components/layout/Sidebar";
import { AppShellProvider } from "@/components/layout/AppShellContext";
import { useAuth } from "@/lib/auth/AuthContext";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [status, router]);

  if (status === "loading") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-3 bg-background">
        <Loader2 className="h-6 w-6 animate-spin text-primary" aria-hidden="true" />
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-subtle">Loading control plane</p>
      </div>
    );
  }

  if (status === "unauthenticated") {
    return null;
  }

  return (
    <AppShellProvider>
      <div className="flex h-screen overflow-hidden bg-background">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">{children}</div>
      </div>
    </AppShellProvider>
  );
}
