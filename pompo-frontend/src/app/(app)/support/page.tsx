"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { MonoId } from "@/components/ui/Table";
import { useAuth } from "@/lib/auth/AuthContext";
import { customersService, type SupportRequest } from "@/lib/api/services/customers";

export default function SupportPage() {
  const { isDemoSession } = useAuth();
  const [rows, setRows] = useState<SupportRequest[] | null>(null);

  useEffect(() => {
    void customersService.supportRequests().then((result) => {
      setRows(result.status === "success" ? result.data : []);
    });
  }, []);

  return (
    <PageShell
      title="Support requests"
      breadcrumb={[{ label: "Operations" }, { label: "Support" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Lightweight customer reports. This is not a ticketing platform. Payment
        references are preserved; internal logs are not shown.
      </p>
      <Card>
        <CardHeader>
          <CardTitle>Open and recent requests</CardTitle>
        </CardHeader>
        <CardBody>
          {rows === null ? (
            <p className="text-sm text-text-muted">Loading…</p>
          ) : rows.length === 0 ? (
            <EmptyState title="No support requests" />
          ) : (
            <div className="space-y-3">
              {rows.map((row) => (
                <div key={row.id} className="rounded-lg border border-border p-3">
                  <div className="flex items-center justify-between gap-3">
                    <p className="font-medium">{row.subject}</p>
                    <span className="text-xs uppercase text-text-muted">{row.status}</span>
                  </div>
                  <p className="mt-1 text-sm text-text-muted">{row.message}</p>
                  <div className="mt-2 flex flex-wrap gap-3 text-xs text-text-muted">
                    <span>{row.category}</span>
                    <MonoId>{row.public_identifier}</MonoId>
                    {row.payment_reference ? <MonoId>{row.payment_reference}</MonoId> : null}
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
