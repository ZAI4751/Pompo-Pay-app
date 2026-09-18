"use client";

import { useEffect, useState } from "react";
import { paymentRequestsService } from "@/lib/api/services/paymentRequests";
import type { PaymentRequest } from "@/lib/api/services/paymentRequests";
import { formatMoney, humanizeCustomerError } from "@/lib/checkout/publicCheckout";

const STATUS_LABELS: Record<string, string> = {
  pending: "Pending",
  paid: "Paid",
  cancelled: "Cancelled",
  expired: "Expired",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "text-warning",
  paid: "text-success",
  cancelled: "text-text-subtle",
  expired: "text-error",
};

function RequestCard({
  req,
  onCancel,
}: {
  req: PaymentRequest;
  onCancel: (id: string) => void;
}) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleCancel = async () => {
    setLoading(true);
    setError("");
    const res = await paymentRequestsService.cancel(req.public_identifier);
    setLoading(false);
    if (res.status === "success") {
      onCancel(req.public_identifier);
    } else {
      setError(humanizeCustomerError(res.message, "Could not cancel."));
    }
  };

  const created = req.created_at ? new Date(req.created_at) : null;

  return (
    <li className="card-depth rounded-2xl border border-border bg-surface px-4 py-3">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="truncate text-sm font-semibold text-text">
            {req.description || "Payment request"}
          </p>
          <p className="mt-0.5 font-mono text-[11px] text-text-subtle">{req.share_code}</p>
          {created ? (
            <p className="mt-0.5 text-[11px] text-text-subtle">
              {created.toLocaleDateString()} {created.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
            </p>
          ) : null}
        </div>
        <div className="text-right shrink-0">
          <p className="text-sm font-semibold tabular-nums text-text">
            {formatMoney(String(req.amount), req.currency)}
          </p>
          <p className={`mt-1 text-[11px] font-medium uppercase tracking-wide ${STATUS_COLORS[req.status] ?? "text-text-subtle"}`}>
            {STATUS_LABELS[req.status] ?? req.status}
          </p>
          {req.payment_reference ? (
            <p className="mt-1 font-mono text-[10px] text-text-subtle">{req.payment_reference}</p>
          ) : null}
        </div>
      </div>

      {error ? (
        <p className="mt-2 rounded-lg bg-error-bg px-2 py-1 text-[11px] text-error">{error}</p>
      ) : null}

      {req.status === "pending" ? (
        <button
          id={`cancel-request-${req.public_identifier}`}
          type="button"
          disabled={loading}
          onClick={() => void handleCancel()}
          className="mt-3 w-full rounded-xl border border-border py-2 text-xs font-semibold text-text-muted disabled:opacity-40"
        >
          {loading ? "Cancelling…" : "Cancel request"}
        </button>
      ) : null}
    </li>
  );
}

export default function AccountRequestsPage() {
  const [rows, setRows] = useState<PaymentRequest[] | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    void paymentRequestsService.listMine().then((res) => {
      if (!active) return;
      if (res.status === "success") {
        setRows(res.data);
        return;
      }
      setError(humanizeCustomerError(res.message, "Could not load your payment requests."));
      setRows([]);
    });
    return () => {
      active = false;
    };
  }, []);

  const handleCancelled = (id: string) => {
    setRows((prev) =>
      prev
        ? prev.map((r) => (r.public_identifier === id ? { ...r, status: "cancelled" } : r))
        : prev,
    );
  };

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Payment Requests</h1>
      <p className="mt-1 text-sm text-text-muted">
        Requests you have sent to others via POMPO.
      </p>

      {error ? (
        <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p>
      ) : null}
      {rows === null ? (
        <p className="mt-6 text-sm text-text-muted">Loading payment requests…</p>
      ) : null}
      {rows && rows.length === 0 && !error ? (
        <p className="mt-6 text-sm text-text-muted">
          You have not sent any payment requests yet.
        </p>
      ) : null}

      <ul className="mt-4 space-y-2">
        {(rows || []).map((req) => (
          <RequestCard key={req.public_identifier} req={req} onCancel={handleCancelled} />
        ))}
      </ul>
    </section>
  );
}
