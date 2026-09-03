"use client";

import { useEffect, useState } from "react";
import { customersService, type SupportRequest } from "@/lib/api/services/customers";
import { formatReceiptTimestamp, humanizeCustomerError } from "@/lib/checkout/publicCheckout";

const CATEGORIES = [
  { value: "payment_problem", label: "Payment problem" },
  { value: "report_transaction", label: "Report a transaction" },
  { value: "reference_lookup", label: "Reference lookup" },
  { value: "other", label: "Other" },
];

export default function AccountCarePage() {
  const [rows, setRows] = useState<SupportRequest[] | null>(null);
  const [category, setCategory] = useState("payment_problem");
  const [subject, setSubject] = useState("");
  const [message, setMessage] = useState("");
  const [paymentReference, setPaymentReference] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);

  const load = async () => {
    const res = await customersService.supportRequests();
    if (res.status === "success") {
      setRows(res.data);
      return;
    }
    setError(humanizeCustomerError(res.message, "Could not load support requests."));
    setRows([]);
  };

  useEffect(() => {
    let active = true;
    void customersService.supportRequests().then((res) => {
      if (!active) return;
      if (res.status === "success") {
        setRows(res.data);
        return;
      }
      setError(humanizeCustomerError(res.message, "Could not load support requests."));
      setRows([]);
    });
    return () => {
      active = false;
    };
  }, []);

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Customer care</h1>
      <p className="mt-1 text-sm text-text-muted">Create and view support requests on your POMPO account.</p>

      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {notice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{notice}</p> : null}

      <form
        className="card-depth mt-4 space-y-3 rounded-2xl border border-border bg-surface px-4 py-4"
        onSubmit={(event) => {
          event.preventDefault();
          setBusy(true);
          setError("");
          setNotice("");
          void customersService
            .createSupportRequest({
              category,
              subject: subject.trim(),
              message: message.trim(),
              payment_reference: paymentReference.trim() || undefined,
            })
            .then((res) => {
              if (res.status === "error") {
                setError(humanizeCustomerError(res.message, "Could not create the support request."));
                return;
              }
              setSubject("");
              setMessage("");
              setPaymentReference("");
              setNotice("Support request created.");
              return load();
            })
            .finally(() => setBusy(false));
        }}
      >
        <label className="block text-xs font-medium text-text-muted">
          Category
          <select
            value={category}
            onChange={(event) => setCategory(event.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text"
          >
            {CATEGORIES.map((item) => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-xs font-medium text-text-muted">
          Subject
          <input
            required
            value={subject}
            onChange={(event) => setSubject(event.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
          />
        </label>
        <label className="block text-xs font-medium text-text-muted">
          Message
          <textarea
            required
            rows={4}
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
          />
        </label>
        <label className="block text-xs font-medium text-text-muted">
          Payment reference <span className="text-text-subtle">(optional)</span>
          <input
            value={paymentReference}
            onChange={(event) => setPaymentReference(event.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
          />
        </label>
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
        >
          {busy ? "Sending…" : "Submit request"}
        </button>
      </form>

      <h2 className="mt-8 text-sm font-semibold text-text">Your requests</h2>
      {rows === null ? <p className="mt-3 text-sm text-text-muted">Loading…</p> : null}
      {rows && rows.length === 0 ? <p className="mt-3 text-sm text-text-muted">No support requests yet.</p> : null}
      <ul className="mt-3 space-y-2">
        {(rows || []).map((row) => (
          <li key={row.id} className="rounded-2xl border border-border bg-surface px-4 py-3">
            <p className="text-sm font-semibold text-text">{row.subject}</p>
            <p className="mt-1 text-xs text-text-muted">{row.message}</p>
            <p className="mt-2 text-[11px] uppercase tracking-wide text-text-subtle">
              {row.status} · {row.public_identifier}
              {row.payment_reference ? ` · ${row.payment_reference}` : ""}
            </p>
            <p className="mt-1 text-[11px] text-text-subtle">
              {formatReceiptTimestamp(row.created_at) || ""}
            </p>
          </li>
        ))}
      </ul>
    </section>
  );
}
