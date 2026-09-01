"use client";

import { Toaster, toast } from "sonner";
import { useTheme } from "next-themes";
import type { ReactNode } from "react";

type ToastTone = "success" | "error" | "info";

interface ToastContextValue {
  push: (message: string, tone?: ToastTone) => void;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const { resolvedTheme } = useTheme();
  return (
    <>
      {children}
      <Toaster
        position="bottom-right"
        closeButton
        duration={3800}
        theme={resolvedTheme === "dark" ? "dark" : "light"}
        toastOptions={{
          classNames: {
            toast:
              "border border-border bg-surface text-text shadow-glow font-sans text-sm",
            title: "text-text",
            description: "text-text-muted",
            success: "border-success/30",
            error: "border-error/30",
            info: "border-info/30",
          },
        }}
      />
    </>
  );
}

export function useToast(): ToastContextValue {
  return {
    push(message: string, tone: ToastTone = "info") {
      if (tone === "success") toast.success(message);
      else if (tone === "error") toast.error(message);
      else toast(message);
    },
  };
}
