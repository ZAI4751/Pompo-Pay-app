"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { paymentsService } from "@/lib/api/services/payments";
import type { Payment } from "@/lib/types/payment";
import { formatMoney, formatReceiptTimestamp, humanizeCustomerError } from "@/lib/checkout/publicCheckout";
import { isReceiptEligible } from "@/lib/customer/customerAccount";

export default function AccountReceiptsPage() {
  const [rows, setRows] = useState<Payment[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void paymentsService.listMine().then((res) => {
      if (!active) return;
      if (res.status === "success") {
        setRows(res.data.filter((payment) => isReceiptEligible(payment.status)));
        return;
      }
      setError(humanizeCustomerError(res.message, "Could not load receipts."));
      setRows([]);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Receipts</h1>
      <p className="mt-1 text-sm text-text-muted">Successful payments only. Fields come from POMPO, not invented totals.</p>
      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {rows === null ? <p className="mt-6 text-sm text-text-muted">Loading receipts…</p> : null}
      {rows && rows.length === 0 && !error ? (
        <p className="mt-6 text-sm text-text-muted">No receipts yet.</p>
      ) : null}
      <ul className="mt-4 space-y-2">
        {(rows || []).map((payment) => (
          <li key={payment.reference}>
            <Link
              href={`/account/activity/${encodeURIComponent(payment.reference)}`}
              className="card-depth block rounded-2xl border border-border bg-surface px-4 py-3"
            >
              <p className="text-sm font-semibold text-text">{payment.merchant_name || "Merchant"}</p>
              <p className="mt-1 text-sm tabular-nums text-text">{formatMoney(payment.amount, payment.currency)}</p>
              <p className="mt-1 font-mono text-[11px] text-text-subtle">{payment.reference}</p>
              <p className="mt-1 text-[11px] text-text-subtle">
                {formatReceiptTimestamp(payment.completed_at || payment.created_at) || "Date unavailable"}
              </p>
            </Link>
          </li>
        ))}
      </ul>
    </section>
  );
}
