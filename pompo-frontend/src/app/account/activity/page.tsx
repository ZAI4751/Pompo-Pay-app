"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { paymentsService } from "@/lib/api/services/payments";
import type { Payment } from "@/lib/types/payment";
import { formatMoney, formatReceiptTimestamp, humanizeCustomerError } from "@/lib/checkout/publicCheckout";
import { isReceiptEligible } from "@/lib/customer/customerAccount";

export default function AccountActivityPage() {
  const [rows, setRows] = useState<Payment[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void paymentsService.listMine().then((res) => {
      if (!active) return;
      if (res.status === "success") {
        setRows(res.data);
        return;
      }
      setError(humanizeCustomerError(res.message, "Could not load your payments."));
      setRows([]);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Activity</h1>
      <p className="mt-1 text-sm text-text-muted">Payments you made with this POMPO account.</p>
      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {rows === null ? <p className="mt-6 text-sm text-text-muted">Loading activity…</p> : null}
      {rows && rows.length === 0 && !error ? (
        <p className="mt-6 text-sm text-text-muted">No payments yet.</p>
      ) : null}
      <ul className="mt-4 space-y-2">
        {(rows || []).map((payment) => (
          <li key={payment.reference}>
            <Link
              href={`/account/activity/${encodeURIComponent(payment.reference)}`}
              className="card-depth block rounded-2xl border border-border bg-surface px-4 py-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="truncate text-sm font-semibold text-text">{payment.merchant_name || "Merchant"}</p>
                  <p className="mt-0.5 font-mono text-[11px] text-text-subtle">{payment.reference}</p>
                  <p className="mt-1 text-[11px] text-text-subtle">
                    {formatReceiptTimestamp(payment.completed_at || payment.created_at) || "Date unavailable"}
                  </p>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold tabular-nums text-text">
                    {formatMoney(payment.amount, payment.currency)}
                  </p>
                  <p className="mt-1 text-[11px] uppercase tracking-wide text-text-subtle">{payment.status}</p>
                  {isReceiptEligible(payment.status) ? (
                    <p className="mt-1 text-[11px] font-semibold text-primary">Receipt</p>
                  ) : null}
                </div>
              </div>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
