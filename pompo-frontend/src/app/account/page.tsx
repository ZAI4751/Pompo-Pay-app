"use client";

import { useCustomerSession } from "@/lib/customer/CustomerSessionProvider";
import { isCustomerRole, securityStateCopy } from "@/lib/customer/customerAccount";

export default function AccountProfilePage() {
  const { user } = useCustomerSession();
  if (!user) return null;
  const security = securityStateCopy(user);

  return (
    <section>
      <h1 className="text-xl font-semibold tracking-tight text-text">Account</h1>
      <p className="mt-1 text-sm text-text-muted">Basic profile for this POMPO identity.</p>
      {!isCustomerRole(user.role_code) ? (
        <p className="mt-3 rounded-xl bg-warning-bg px-3 py-2 text-xs text-warning">
          Merchant tools stay in the POMPO app and Master Admin. This page is a lightweight
          customer surface.
        </p>
      ) : null}

      <dl className="card-depth mt-4 space-y-3 rounded-2xl border border-border bg-surface px-4 py-4 text-sm">
        <Row label="Name" value={user.full_name} />
        <Row label="Customer ID" value={user.id} mono />
        <Row label="Email" value={user.email} />
        <Row label="Phone" value={user.phone || "Not on file"} />
        <Row label="Email status" value={security.email} />
        <Row label="Account" value={security.account} />
      </dl>
    </section>
  );
}

function Row({ label, value, mono }: { label: string; value?: string | null; mono?: boolean }) {
  if (!value) return null;
  return (
    <div className="flex items-start justify-between gap-4">
      <dt className="text-text-subtle">{label}</dt>
      <dd className={`text-right font-medium text-text ${mono ? "break-all font-mono text-[11px]" : ""}`}>
        {value}
      </dd>
    </div>
  );
}
