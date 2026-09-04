"use client";

/**
 * Route-group layout for every authenticated screen. Handles the
 * loading/unauthenticated states itself so individual pages never need to
 * -- they can assume `user` exists once rendered.
 */

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { Sidebar } from "@/components/layout/Sidebar";
import { AppShellProvider } from "@/components/layout/AppShellContext";
import { useAuth } from "@/lib/auth/AuthContext";
import { isPlatformAdminRole } from "@/lib/auth/adminEligibility";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { status, user, logout } = useAuth();
  const router = useRouter();
  const adminSession = status === "authenticated" && isPlatformAdminRole(user?.role_code);

  useEffect(() => {
    if (status === "unauthenticated") {
      router.replace("/login");
      return;
    }
    if (status === "authenticated" && !isPlatformAdminRole(user?.role_code)) {
      void logout();
    }
  }, [status, user, logout, router]);

  if (status === "loading") {
    return (
      <div className="flex h-screen flex-col items-center justify-center gap-4 bg-background pompo-aurora">
        <div className="h-10 w-48">
          <div className="skeleton h-3 w-24 rounded" />
          <div className="skeleton mt-3 h-8 w-40 rounded" />
        </div>
        <p className="text-xs font-medium uppercase tracking-[0.16em] text-text-subtle">Loading operations</p>
      </div>
    );
  }

  if (status === "unauthenticated" || !adminSession) {
    return (
      <div className="flex h-screen items-center justify-center bg-background">
        <p className="text-sm text-text-muted">Redirecting to sign in…</p>
      </div>
    );
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
