"use client";

import { FormEvent, useState } from "react";
import { X } from "lucide-react";

export function MoneySheet({
  open,
  mode,
  onClose,
}: {
  open: boolean;
  mode: "send" | "request";
  onClose: () => void;
}) {
  const [amount, setAmount] = useState("100.00");
  const [sent, setSent] = useState(false);

  if (!open) return null;

  function submit(event: FormEvent) {
    event.preventDefault();
    setSent(true);
  }

  const title = mode === "send" ? "Send money" : "Request money";

  return (
    <div className="absolute inset-0 z-20 flex items-end bg-slate-950/40 p-4 backdrop-blur-sm">
      <form
        onSubmit={submit}
        className="w-full rounded-[28px] bg-white p-5 shadow-xl dark:bg-slate-900"
      >
        <div className="flex items-center justify-between">
          <h2 className="text-lg font-semibold text-text">{title}</h2>
          <button
            type="button"
            onClick={() => {
              setSent(false);
              onClose();
            }}
            aria-label="Close"
            className="rounded-full p-1 hover:bg-surface-raised"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        {sent ? (
          <p className="mt-4 text-sm text-text-muted">
            This wallet preview does not move money. Use the mobile app to pay a merchant QR.
          </p>
        ) : (
          <>
            <label className="mt-4 block text-sm font-medium text-text" htmlFor="wallet-amount">
              Amount (MWK)
            </label>
            <input
              id="wallet-amount"
              value={amount}
              onChange={(event) => setAmount(event.target.value)}
              inputMode="decimal"
              className="mt-1.5 h-12 w-full rounded-2xl border border-border bg-surface-inset px-4 text-lg font-semibold tabular-nums text-text outline-none focus-visible:border-primary"
            />
            <button
              type="submit"
              className="mt-4 w-full rounded-full bg-primary py-3 text-sm font-semibold text-primary-foreground transition hover:bg-primary-hover"
            >
              Continue
            </button>
          </>
        )}
      </form>
    </div>
  );
}
