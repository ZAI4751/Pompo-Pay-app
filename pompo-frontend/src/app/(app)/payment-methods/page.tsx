"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Badge } from "@/components/ui/Badge";
import { MonoId, Table, TableBody, TableHead, Td, Th, Tr } from "@/components/ui/Table";
import { useAuth } from "@/lib/auth/AuthContext";
import { instrumentsService, type AdminPaymentMethod } from "@/lib/api/services/instruments";
import type { ApiResult } from "@/lib/types/common";

function methodTone(status: string): "success" | "warning" | "error" | "neutral" | "info" {
  if (status === "active") return "success";
  if (status === "revoked") return "error";
  if (status === "expired" || status === "inactive") return "warning";
  return "neutral";
}

export default function PaymentMethodsAdminPage() {
  const { isDemoSession } = useAuth();
  const [result, setResult] = useState<ApiResult<AdminPaymentMethod[]> | null>(null);

  useEffect(() => {
    void instrumentsService.adminList().then(setResult);
  }, []);

  const rows = result?.status === "success" ? result.data : [];

  return (
    <PageShell
      title="Payment methods"
      breadcrumb={[{ label: "Payments" }, { label: "Payment methods" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Saved customer payment methods. Tokens, PANs, PINs, and CVVs are never
        shown. This is not a wallet and does not store customer currency.
      </p>

      {result === null && <p className="text-sm text-text-muted">Loading registered methods…</p>}

      {result?.status === "error" && (
        <ErrorState kind={result.kind} description={result.message} requestId={result.requestId} />
      )}

      {result?.status === "success" && rows.length === 0 && (
        <EmptyState
          title="No payment methods"
          description="Methods appear after a customer enrolls Airtel Money or a sandbox card."
        />
      )}

      {result?.status === "success" && rows.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle>Registered methods</CardTitle>
          </CardHeader>
          <CardBody className="p-0">
            <Table>
              <TableHead>
                <Th>Customer</Th>
                <Th>Method</Th>
                <Th>Provider</Th>
                <Th>Identifier</Th>
                <Th>Status</Th>
                <Th>Created</Th>
                <Th>Last used</Th>
              </TableHead>
              <TableBody>
                {rows.map((row) => (
                  <Tr key={row.id}>
                    <Td>{row.customer_email ?? "—"}</Td>
                    <Td>
                      <p className="font-medium">{row.display_name}</p>
                      <p className="text-xs text-text-subtle">{row.instrument_type}</p>
                    </Td>
                    <Td>{row.provider_display_name}</Td>
                    <Td>
                      <MonoId>{row.masked_identifier}</MonoId>
                    </Td>
                    <Td>
                      <Badge tone={methodTone(row.status)}>{row.status.toUpperCase()}</Badge>
                      {row.is_sandbox ? <Badge tone="info">SANDBOX</Badge> : null}
                    </Td>
                    <Td>{new Date(row.created_at).toLocaleString()}</Td>
                    <Td>{row.last_used_at ? new Date(row.last_used_at).toLocaleString() : "—"}</Td>
                  </Tr>
                ))}
              </TableBody>
            </Table>
          </CardBody>
        </Card>
      )}
    </PageShell>
  );
}
