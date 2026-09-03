"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { readCustomerNotice, writeCustomerNotice } from "@/lib/customer/sessionStore";
import { authService } from "@/lib/api/services/auth";
import { useCustomerSession } from "@/lib/customer/CustomerSessionProvider";
import { emailDeliveryCopy } from "@/lib/customer/customerAccount";
import { humanizeCustomerError } from "@/lib/checkout/publicCheckout";

export function CustomerAuthCard({ returnTo }: { returnTo: string }) {
  const { signIn } = useCustomerSession();
  const router = useRouter();
  const [mode, setMode] = useState<"login" | "register" | "forgot" | "reactivate">("login");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [error, setError] = useState("");
  const [notice, setNotice] = useState(() => {
    const stored = readCustomerNotice();
    if (stored) writeCustomerNotice(null);
    return stored || "";
  });
  const [submitting, setSubmitting] = useState(false);

  const finish = async (access: string, refresh: string) => {
    const user = await signIn(access, refresh);
    if (!user) {
      setError("Signed in, but your profile could not be loaded.");
      return;
    }
    if (returnTo.startsWith("/p/")) {
      router.push(returnTo);
    }
  };

  const onSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    setError("");
    setNotice("");
    setSubmitting(true);
    try {
      if (mode === "forgot") {
        const res = await authService.forgotPassword(email.trim());
        if (res.status === "success") {
          setNotice(
            emailDeliveryCopy(
              res.data.email_delivery,
              humanizeCustomerError(
                res.data.detail,
                "If an account matches that email, password reset instructions have been sent.",
              ),
            ),
          );
        } else {
          setError(humanizeCustomerError(res.message, "Could not request a password reset."));
        }
        return;
      }
      if (mode === "reactivate") {
        const res = await authService.requestAccountReactivation(email.trim());
        if (res.status === "success") {
          setNotice(
            emailDeliveryCopy(
              res.data.email_delivery,
              humanizeCustomerError(
                res.data.detail,
                "If a deactivated account matches that email, reactivation instructions have been sent.",
              ),
            ),
          );
        } else {
          setError(humanizeCustomerError(res.message, "Could not request account reactivation."));
        }
        return;
      }
      if (mode === "register") {
        const res = await authService.registerCustomer({
          full_name: fullName.trim(),
          phone: phone.trim(),
          email: email.trim(),
          password,
        });
        if (res.status === "success") {
          await finish(res.data.access_token, res.data.refresh_token);
        } else {
          setError(humanizeCustomerError(res.message, "Could not create your account."));
        }
        return;
      }
      const res = await authService.login({ email: email.trim(), password });
      if (res.status === "success") {
        await finish(res.data.access_token, res.data.refresh_token);
        return;
      }
      if (res.kind === "forbidden" || /deactivated/i.test(res.message)) {
        setMode("reactivate");
        setError(humanizeCustomerError(res.message, "This POMPO account is deactivated."));
        return;
      }
      setError(humanizeCustomerError(res.message, "Could not sign in. Check your email and password."));
    } catch {
      setError("Could not reach POMPO. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="card-depth my-auto rounded-2xl border border-border bg-surface p-5">
      <h1 className="text-lg font-semibold text-text">
        {mode === "register" ? "Create a POMPO account" : "Sign in to POMPO"}
      </h1>
      <p className="mt-1 text-sm text-text-muted">Use the same POMPO account as the mobile app.</p>

      {mode === "login" || mode === "register" ? (
        <div className="mt-4 grid grid-cols-2 rounded-xl bg-surface-inset p-1">
          <button
            type="button"
            onClick={() => setMode("login")}
            className={`rounded-lg py-2 text-xs font-semibold ${mode === "login" ? "bg-surface text-text" : "text-text-muted"}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setMode("register")}
            className={`rounded-lg py-2 text-xs font-semibold ${mode === "register" ? "bg-surface text-text" : "text-text-muted"}`}
          >
            Create account
          </button>
        </div>
      ) : null}

      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {notice ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{notice}</p> : null}

      <form onSubmit={(event) => void onSubmit(event)} className="mt-4 space-y-3">
        {mode === "register" ? (
          <>
            <Field label="Full name" value={fullName} onChange={setFullName} autoComplete="name" />
            <Field label="Phone" value={phone} onChange={setPhone} type="tel" autoComplete="tel" />
          </>
        ) : null}
        <Field label="Email" value={email} onChange={setEmail} type="email" autoComplete="email" />
        {mode === "login" || mode === "register" ? (
          <Field
            label="Password"
            value={password}
            onChange={setPassword}
            type="password"
            autoComplete={mode === "login" ? "current-password" : "new-password"}
          />
        ) : null}
        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
        >
          {submitting
            ? "Please wait…"
            : mode === "register"
              ? "Create account"
              : mode === "forgot"
                ? "Send reset instructions"
                : mode === "reactivate"
                  ? "Request reactivation"
                  : "Sign in"}
        </button>
      </form>

      {mode === "login" ? (
        <div className="mt-3 flex flex-col gap-2">
          <button type="button" onClick={() => setMode("forgot")} className="text-xs font-semibold text-primary">
            Forgot password?
          </button>
          <button type="button" onClick={() => setMode("reactivate")} className="text-xs font-semibold text-text-muted">
            Reactivate a deactivated account
          </button>
        </div>
      ) : (
        <button type="button" onClick={() => setMode("login")} className="mt-3 text-xs font-semibold text-text-muted">
          Back to sign in
        </button>
      )}
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
  autoComplete,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  autoComplete?: string;
}) {
  return (
    <label className="block text-xs font-medium text-text-muted">
      {label}
      <input
        type={type}
        required
        autoComplete={autoComplete}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
      />
    </label>
  );
}
