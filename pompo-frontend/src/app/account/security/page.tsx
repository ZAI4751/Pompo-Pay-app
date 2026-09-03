"use client";

import { useState } from "react";
import { authService } from "@/lib/api/services/auth";
import { useCustomerSession } from "@/lib/customer/CustomerSessionProvider";
import { writeCustomerNotice } from "@/lib/customer/sessionStore";
import {
  confirmationMatchesDeactivate,
  DEACTIVATION_CONFIRMATION,
  emailDeliveryCopy,
  securityStateCopy,
} from "@/lib/customer/customerAccount";
import { humanizeCustomerError } from "@/lib/checkout/publicCheckout";

export default function AccountSecurityPage() {
  const { user, logoutAllSessions, refreshProfile, clearSession } = useCustomerSession();
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [deactivatePassword, setDeactivatePassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmingDeactivate, setConfirmingDeactivate] = useState(false);

  if (!user) return null;
  const security = securityStateCopy(user);

  const run = async (work: () => Promise<void>) => {
    setBusy(true);
    setError("");
    setMessage("");
    try {
      await work();
    } catch {
      setError("Could not reach POMPO. Please try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Password & security</h1>
      <p className="mt-1 text-sm text-text-muted">These controls call the live POMPO account APIs.</p>

      <dl className="card-depth mt-4 space-y-3 rounded-2xl border border-border bg-surface px-4 py-4 text-sm">
        <div className="flex justify-between gap-4">
          <dt className="text-text-subtle">Email</dt>
          <dd className="font-medium text-text">{security.email}</dd>
        </div>
        <div className="flex justify-between gap-4">
          <dt className="text-text-subtle">Account</dt>
          <dd className="font-medium text-text">{security.account}</dd>
        </div>
        <div>
          <dt className="text-text-subtle">Two-factor authentication</dt>
          <dd className="mt-1 text-sm text-text-muted">{security.mfa}</dd>
        </div>
      </dl>

      {error ? <p className="mt-3 rounded-lg bg-error-bg px-3 py-2 text-xs text-error">{error}</p> : null}
      {message ? <p className="mt-3 rounded-lg bg-success-bg px-3 py-2 text-xs text-success">{message}</p> : null}

      <form
        className="mt-6 space-y-3"
        onSubmit={(event) => {
          event.preventDefault();
          void run(async () => {
            const res = await authService.changePassword(currentPassword, newPassword);
            if (res.status === "error") {
              setError(humanizeCustomerError(res.message, "Could not change password."));
              return;
            }
            setCurrentPassword("");
            setNewPassword("");
            setMessage("Password changed. Use the new password next time you sign in.");
          });
        }}
      >
        <h2 className="text-sm font-semibold text-text">Change password</h2>
        <Field label="Current password" value={currentPassword} onChange={setCurrentPassword} type="password" />
        <Field label="New password" value={newPassword} onChange={setNewPassword} type="password" />
        <button
          type="submit"
          disabled={busy}
          className="w-full rounded-xl bg-primary py-3 text-sm font-semibold text-primary-foreground disabled:opacity-50"
        >
          Update password
        </button>
      </form>

      <div className="mt-6 space-y-2">
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const res = await authService.requestEmailVerification(user.email);
              if (res.status === "error") {
                setError(humanizeCustomerError(res.message, "Could not request verification."));
                return;
              }
              setMessage(
                emailDeliveryCopy(
                  res.data.email_delivery,
                  humanizeCustomerError(res.data.detail, "Verification instructions were requested."),
                ),
              );
              await refreshProfile();
            })
          }
          className="w-full rounded-xl border border-border py-3 text-sm font-semibold text-text disabled:opacity-50"
        >
          Request email verification
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() =>
            void run(async () => {
              const res = await logoutAllSessions();
              if (!res.ok) {
                setError(humanizeCustomerError(res.message, "Could not sign out other sessions."));
              }
            })
          }
          className="w-full rounded-xl border border-border py-3 text-sm font-semibold text-text disabled:opacity-50"
        >
          Sign out all sessions
        </button>
      </div>

      <div className="mt-10 rounded-2xl border border-error/30 bg-error-bg px-4 py-4">
        <h2 className="text-sm font-semibold text-error">Danger zone</h2>
        <p className="mt-2 text-xs leading-relaxed text-text-muted">
          Deactivating stops this account from signing in and revokes refresh sessions. Payment
          records and receipts are kept. This is not a delete.
        </p>
        {!confirmingDeactivate ? (
          <button
            type="button"
            onClick={() => setConfirmingDeactivate(true)}
            className="mt-4 w-full rounded-xl bg-error py-3 text-sm font-semibold text-white"
          >
            Deactivate account
          </button>
        ) : (
          <form
            className="mt-4 space-y-3"
            onSubmit={(event) => {
              event.preventDefault();
              if (!confirmationMatchesDeactivate(confirmation)) {
                setError(`Type ${DEACTIVATION_CONFIRMATION} to confirm.`);
                return;
              }
              void run(async () => {
                const res = await authService.deactivateAccount(deactivatePassword, confirmation.trim());
                if (res.status === "error") {
                  setError(humanizeCustomerError(res.message, "Account was not deactivated."));
                  return;
                }
                writeCustomerNotice(
                  "Your account is deactivated. Payments and receipts remain on file. Contact POMPO customer care if you need help returning.",
                );
                clearSession();
              });
            }}
          >
            <Field
              label="Current password"
              value={deactivatePassword}
              onChange={setDeactivatePassword}
              type="password"
            />
            <Field
              label={`Type ${DEACTIVATION_CONFIRMATION} to confirm`}
              value={confirmation}
              onChange={setConfirmation}
            />
            <button
              type="submit"
              disabled={busy}
              className="w-full rounded-xl bg-error py-3 text-sm font-semibold text-white disabled:opacity-50"
            >
              Deactivate this account
            </button>
            <button
              type="button"
              onClick={() => setConfirmingDeactivate(false)}
              className="w-full text-xs font-semibold text-text-muted"
            >
              Cancel
            </button>
          </form>
        )}
      </div>
    </section>
  );
}

function Field({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
}) {
  return (
    <label className="block text-xs font-medium text-text-muted">
      {label}
      <input
        type={type}
        required
        value={value}
        onChange={(event) => onChange(event.target.value)}
        className="mt-1 w-full rounded-xl border border-border bg-background px-3 py-2.5 text-sm text-text outline-none focus:border-primary"
      />
    </label>
  );
}
