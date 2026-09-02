"use client";

import { ScanLine, X } from "lucide-react";

export function ScanModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="absolute inset-0 z-20 flex items-end bg-slate-950/40 p-4 backdrop-blur-sm sm:items-center sm:justify-center">
      <div role="dialog" aria-labelledby="scan-title" className="w-full rounded-[28px] bg-white p-5 shadow-xl dark:bg-slate-900">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h2 id="scan-title" className="text-lg font-semibold text-text">
              Scan a merchant QR
            </h2>
            <p className="mt-1 text-sm text-text-muted">
              Live checkout lives in the Pompo mobile app. This preview shows where the scan action sits in the wallet.
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close" className="rounded-full p-1 hover:bg-surface-raised">
            <X className="h-5 w-5" />
          </button>
        </div>
        <div className="mt-5 flex h-40 items-center justify-center rounded-3xl border border-dashed border-border bg-surface-inset">
          <ScanLine className="h-12 w-12 text-primary" />
        </div>
        <button
          type="button"
          onClick={onClose}
          className="mt-4 w-full rounded-full bg-primary py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover"
        >
          Got it
        </button>
      </div>
    </div>
  );
}
