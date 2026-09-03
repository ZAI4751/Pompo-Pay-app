"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { MonoId } from "@/components/ui/Table";
import { useAuth } from "@/lib/auth/AuthContext";
import { instrumentsService, type AdminPaymentMethod } from "@/lib/api/services/instruments";

export default function PaymentMethodsAdminPage() {
  const { isDemoSession } = useAuth();
  const [rows, setRows] = useState<AdminPaymentMethod[] | null>(null);

  useEffect(() => {
    void instrumentsService.adminList().then((result) => {
      setRows(result.status === "success" ? result.data : []);
    });
  }, []);

  return (
    <PageShell
      title="Payment methods"
      breadcrumb={[{ label: "Operations" }, { label: "Payment methods" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Saved customer payment methods. Tokens, PANs, PINs, and CVVs are never
        shown. This is not a wallet.
      </p>
      <Card>
        <CardHeader>
          <CardTitle>Registered methods</CardTitle>
        </CardHeader>
        <CardBody>
          {rows === null ? (
            <p className="text-sm text-text-muted">Loading…</p>
          ) : rows.length === 0 ? (
            <EmptyState title="No payment methods" />
          ) : (
            <div className="space-y-3">
              {rows.map((row) => (
                <div key={row.id} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{row.display_name}</p>
                    <span className="text-xs uppercase text-text-muted">{row.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-text-muted">{row.masked_identifier}</p>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-text-muted">
                    <span>{row.provider_display_name}</span>
                    <span>{row.instrument_type}</span>
                    {row.is_sandbox ? <span>TEST</span> : null}
                    {row.customer_email ? <span>{row.customer_email}</span> : null}
                    <MonoId>{row.id}</MonoId>
                    {row.last_used_at ? <span>Last used {row.last_used_at}</span> : null}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardBody>
      </Card>
    </PageShell>
  );
}
