"use client";

import { ThemeProvider } from "next-themes";
import { AuthProvider } from "@/lib/auth/AuthContext";
import { CustomerSessionProvider } from "@/lib/customer/CustomerSessionProvider";
import { ToastProvider } from "@/components/ui/Toast";
import { MotionProvider } from "@/components/motion/MotionProvider";

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <MotionProvider>
        <ToastProvider>
          <AuthProvider>
            <CustomerSessionProvider>{children}</CustomerSessionProvider>
          </AuthProvider>
        </ToastProvider>
      </MotionProvider>
    </ThemeProvider>
  );
}
