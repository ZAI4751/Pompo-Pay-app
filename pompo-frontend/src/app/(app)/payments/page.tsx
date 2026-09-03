"use client";

import { useEffect, useState, type FormEvent } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { MonoId, Table, TableBody, TableHead, Td, Th, Tr } from "@/components/ui/Table";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { paymentsService } from "@/lib/api/services/payments";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import { celebrateSuccess } from "@/lib/celebrate";
import { formatMwk } from "@/lib/format/money";
import type { Payment } from "@/lib/types/payment";
import type { ApiResult } from "@/lib/types/common";
import type { TransactionStatus } from "@/lib/types/transaction";

function asTxnStatus(status: string): TransactionStatus {
  const known: TransactionStatus[] = [
    "created",
    "qr_generated",
    "pending",
    "pending_user_pin",
    "processing",
    "success",
    "failed",
    "timeout",
    "cancelled",
    "refunded",
  ];
  return known.includes(status as TransactionStatus) ? (status as TransactionStatus) : "created";
}

export default function PaymentsPage() {
  const { isDemoSession, user } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [reference, setReference] = useState("");
  const [result, setResult] = useState<ApiResult<Payment> | null>(null);
  const [loading, setLoading] = useState(false);
  const [list, setList] = useState<ApiResult<Payment[]> | null>(null);
  const merchantScoped = Boolean(user?.merchant_id);

  useEffect(() => {
    if (!merchantScoped) {
      return;
    }
    void paymentsService.list({ limit: 50 }).then(setList);
  }, [merchantScoped]);

  async function lookup(event: FormEvent) {
    event.preventDefault();
    setLoading(true);
    const found = await paymentsService.getByReference(reference.trim());
    setResult(found);
    setLoading(false);
  }

  async function cancel() {
    const cancelled = await paymentsService.cancel(reference.trim());
    setResult(cancelled);
    if (cancelled.status === "success") push("Payment cancel requested", "success");
    else push(cancelled.message, "error");
  }

  async function process() {
    const processed = await paymentsService.process(reference.trim());
    setResult(processed);
    if (processed.status === "success") {
      push("Payment processed", "success");
      if (processed.data.status === "success") {
        void celebrateSuccess();
      }
    } else {
      push(processed.message, "error");
    }
  }

  return (
    <PageShell
      title="Payments"
      breadcrumb={[{ label: "Payments" }, { label: "Payments" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        {merchantScoped
          ? "Merchant-scoped payment list from GET /payments. Lookup by reference still works for a single receipt."
          : "Platform administrators have no global payment list. Use reference lookup, or open a merchant-scoped operator session. This page will not invent a ledger."}
      </p>

      {merchantScoped && list?.status === "error" && (
        <ErrorState kind={list.kind} description={list.message} requestId={list.requestId} />
      )}

      {merchantScoped && list?.status === "success" && list.data.length === 0 && (
        <EmptyState
          title="No payments for this merchant"
          description="Payments appear after a till accepts a checkout. Empty is a real result."
        />
      )}

      {merchantScoped && list?.status === "success" && list.data.length > 0 && (
        <div className="mb-4">
          <Table>
            <TableHead>
              <Th>Reference</Th>
              <Th>Amount</Th>
              <Th>Status</Th>
              <Th>Method</Th>
              <Th>Created</Th>
            </TableHead>
            <TableBody>
              {list.data.map((row) => (
                <Tr
                  key={row.id}
                  className="cursor-pointer"
                  onClick={() => {
                    setReference(row.reference);
                    void paymentsService.getByReference(row.reference).then(setResult);
                  }}
                >
                  <Td>
                    <MonoId>{row.reference}</MonoId>
                    <div className="text-xs text-text-subtle">{row.merchant_name ?? row.merchant_id}</div>
                  </Td>
                  <Td>{formatMwk(row.amount)}</Td>
                  <Td>
                    <StatusBadge status={asTxnStatus(row.status)} />
                  </Td>
                  <Td>{row.payment_method}</Td>
                  <Td>{row.created_at ? new Date(row.created_at).toLocaleString() : "—"}</Td>
                </Tr>
              ))}
            </TableBody>
          </Table>
        </div>
      )}

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Look up by reference</CardTitle>
        </CardHeader>
        <CardBody>
          <form className="flex flex-col gap-3 sm:flex-row sm:items-end" onSubmit={(e) => void lookup(e)}>
            <div className="max-w-sm flex-1">
              <Input
                label="Payment reference"
                value={reference}
                onChange={(e) => setReference(e.target.value)}
                required
              />
            </div>
            <Button type="submit" loading={loading}>
              Retrieve
            </Button>
          </form>
        </CardBody>
      </Card>

      {result?.status === "error" && (
        <ErrorState kind={result.kind} description={result.message} requestId={result.requestId} />
      )}

      {result?.status === "success" && (
        <Card>
          <CardHeader className="flex items-center justify-between">
            <div>
              <CardTitle>{result.data.reference}</CardTitle>
              <p className="text-xs text-text-muted">
                <MonoId>{result.data.id}</MonoId>
              </p>
            </div>
            <StatusBadge status={asTxnStatus(result.data.status)} />
          </CardHeader>
          <CardBody className="space-y-3">
            <dl className="grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
              <div>
                <dt className="text-text-subtle">Amount</dt>
                <dd className="font-semibold tabular-nums">{formatMwk(result.data.amount)}</dd>
              </div>
              <div>
                <dt className="text-text-subtle">Method</dt>
                <dd>{result.data.payment_method}</dd>
              </div>
              <div>
                <dt className="text-text-subtle">Failure</dt>
                <dd>{result.data.failure_reason ?? "—"}</dd>
              </div>
            </dl>
            <div className="flex gap-2">
              {hasPermission("transactions:cancel") && (
                <Button variant="secondary" size="sm" onClick={() => void cancel()}>
                  Cancel
                </Button>
              )}
              {hasPermission("transactions:update") && (
                <Button size="sm" onClick={() => void process()}>
                  Process
                </Button>
              )}
            </div>
            {result.data.attempts.length > 0 && (
              <div>
                <p className="mb-2 text-xs font-semibold uppercase tracking-[0.12em] text-text-subtle">
                  Attempts
                </p>
                <ul className="space-y-1 text-sm">
                  {result.data.attempts.map((attempt) => (
                    <li key={attempt.id} className="text-text-muted">
                      #{attempt.attempt_number} {attempt.status}
                      {attempt.provider_reference ? ` · ${attempt.provider_reference}` : ""}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </CardBody>
        </Card>
      )}
    </PageShell>
  );
}
