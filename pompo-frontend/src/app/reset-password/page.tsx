"use client";

import { Suspense, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckoutShell } from "@/components/checkout/CheckoutShell";
import { authService } from "@/lib/api/services/auth";
import { humanizeCustomerError } from "@/lib/checkout/publicCheckout";

function ResetPasswordForm() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token") || "";
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError("");
    setNotice("");
    if (!token) {
      setError("This reset link is missing a token. Request a new one from checkout.");
      return;
    }
    setSubmitting(true);
    try {
      const res = await authService.resetPassword(token, password);
      if (res.status === "success") {
        setNotice(humanizeCustomerError(res.data.detail, "Password has been reset. You can return to checkout and sign in."));
      } else {
        setError(humanizeCustomerError(res.message, "This reset link is invalid or has expired."));
      }
    } catch {
      setError("Could not reach POMPO. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="card-depth my-auto rounded-2xl border border-border bg-surface p-5">
      <h1 className="text-lg font-semibold text-text">Set a new password</h1>
      <p className="mt-1 text-sm text-text-muted">This uses your existing POMPO account.</p>
      {notice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{notice}</p> : null}
      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      <form onSubmit={onSubmit} className="mt-4 space-y-3">
        <label className="block text-xs font-medium text-text-muted">
          New password
          <input
            type="password"
            required
            minLength={8}
            autoComplete="new-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
          />
        </label>
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
        >
          {submitting ? "Please wait…" : "Update password"}
        </button>
      </form>
    </section>
  );
}

export default function ResetPasswordPage() {
  return (
    <CheckoutShell>
      <Suspense fallback={<p className="text-sm text-text-muted">Loading…</p>}>
        <ResetPasswordForm />
      </Suspense>
    </CheckoutShell>
  );
}
