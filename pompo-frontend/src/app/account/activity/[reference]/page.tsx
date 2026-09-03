"use client";

import { use, useEffect, useState } from "react";
import Link from "next/link";
import { paymentsService } from "@/lib/api/services/payments";
import type { Payment, PaymentReceipt } from "@/lib/types/payment";
import { formatMoney, formatReceiptTimestamp, humanizeCustomerError } from "@/lib/checkout/publicCheckout";
import { isReceiptEligible } from "@/lib/customer/customerAccount";

interface PageProps {
  params: Promise<{ reference: string }>;
}

export default function AccountPaymentReceiptPage({ params }: PageProps) {
  const { reference } = use(params);
  const decoded = decodeURIComponent(reference);
  const [payment, setPayment] = useState<Payment | null>(null);
  const [receipt, setReceipt] = useState<PaymentReceipt | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void (async () => {
      const payRes = await paymentsService.getByReference(decoded);
      if (!active) return;
      if (payRes.status !== "success") {
        setError(humanizeCustomerError(payRes.message, "This payment is not available on your account."));
        return;
      }
      setPayment(payRes.data);
      if (!isReceiptEligible(payRes.data.status)) {
        return;
      }
      const receiptRes = await paymentsService.getReceipt(decoded);
      if (!active) return;
      if (receiptRes.status === "success") {
        setReceipt(receiptRes.data);
      } else {
        setError(humanizeCustomerError(receiptRes.message, "A receipt is only available for a successful payment."));
      }
    })();
    return () => {
      active = false;
    };
  }, [decoded]);

  const amount = receipt?.amount ?? payment?.amount;
  const currency = receipt?.currency ?? payment?.currency ?? "MWK";

  return (
    <section>
      <Link href="/account/activity" className="text-xs font-semibold text-primary">
        Back to activity
      </Link>
      <h1 className="mt-3 text-xl font-semibold tracking-tight text-text">
        {receipt ? "Payment receipt" : "Payment"}
      </h1>
      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {!payment && !error ? <p className="mt-6 text-sm text-text-muted">Loading…</p> : null}

      {payment ? (
        <div id="pompo-receipt" className="card-depth mt-4 rounded-2xl border border-border bg-surface px-4 py-5">
          <p className="text-[11px] font-semibold uppercase tracking-brand text-text-subtle">POMPO</p>
          <dl className="mt-4 space-y-3 text-sm">
            <Row label="Merchant" value={receipt?.merchant_name || payment.merchant_name} />
            <Row label="Branch" value={receipt?.branch_name || payment.branch_name} />
            <Row label="Till" value={receipt?.till_name || payment.till_name} />
            <Row label="Amount" value={formatMoney(amount, currency)} />
            <Row label="Status" value={receipt?.customer_status || payment.status} />
            <Row label="Reference" value={receipt?.reference || payment.reference} mono />
            {receipt?.receipt_number ? <Row label="Receipt" value={receipt.receipt_number} mono /> : null}
            <Row
              label="Date"
              value={formatReceiptTimestamp(receipt?.completed_at || receipt?.issued_at || payment.completed_at || payment.created_at)}
            />
            <Row label="Description" value={receipt?.description || payment.description} />
          </dl>
          {receipt?.disclaimer ? <p className="mt-5 text-[11px] leading-relaxed text-text-subtle">{receipt.disclaimer}</p> : null}
        </div>
      ) : null}

      {receipt ? (
        <button
          type="button"
          onClick={() => window.print()}
          className="mt-4 w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground"
        >
          Save or print receipt
        </button>
      ) : null}
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-text-subtle">{label}</dt>
      <dd className={`text-right font-medium text-text ${mono ? "break-all font-mono text-[11px]" : ""}`}>{value}</dd>
    </div>
  );
}
