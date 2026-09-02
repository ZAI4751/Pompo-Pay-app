"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { Badge } from "@/components/ui/Badge";
import { Modal } from "@/components/ui/Modal";
import { Card, CardBody, CardEyebrow, CardTitle } from "@/components/ui/Card";
import { settlementsService } from "@/lib/api/services/settlements";
import { usePermissions } from "@/lib/auth/usePermissions";
import { formatMwk } from "@/lib/format/money";
import type { SettlementRecord, SettlementSummary } from "@/lib/types/settlement";
import type { ApiResult } from "@/lib/types/common";

function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return formatMwk(value);
}

function settlementTone(status: string): "success" | "warning" | "error" | "info" | "neutral" {
  if (status === "reconciled" || status === "settled") return "success";
  if (status === "processing" || status === "received") return "info";
  if (status === "exception") return "error";
  return "neutral";
}

export default function SettlementsPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("settlements:read");
  const [list, setList] = useState<ApiResult<SettlementRecord[]> | null>(null);
  const [summary, setSummary] = useState<ApiResult<SettlementSummary> | null>(null);
  const [selected, setSelected] = useState<SettlementRecord | null>(null);

  useEffect(() => {
    if (!canRead) return;
    void settlementsService.list({ limit: 50 }).then(setList);
    void settlementsService.summary().then(setSummary);
  }, [canRead]);

  return (
    <PageShell title="Settlements" breadcrumb={[{ label: "Operations" }, { label: "Settlements" }]}>
      {!canRead && (
        <ErrorState kind="forbidden" description="You do not have permission to view settlements." />
      )}

      {canRead && (list === null || summary === null) && (
        <div className="grid gap-3 md:grid-cols-4">
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {canRead && summary?.status === "success" && (
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
          <Card>
            <CardBody>
              <CardEyebrow>Count</CardEyebrow>
              <CardTitle>{summary.data.total_settlements}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Gross</CardEyebrow>
              <CardTitle>{money(summary.data.total_gross)}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Provider fees</CardEyebrow>
              <CardTitle>{money(summary.data.total_provider_fees)}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>POMPO fees</CardEyebrow>
              <CardTitle>{money(summary.data.total_pompo_fees)}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Merchant net</CardEyebrow>
              <CardTitle>{money(summary.data.total_merchant_net)}</CardTitle>
            </CardBody>
          </Card>
        </div>
      )}

      {canRead && list?.status === "error" && (
        <ErrorState kind={list.kind} description={list.message} requestId={list.requestId} />
      )}

      {canRead && list?.status === "success" && list.data.length === 0 && (
        <EmptyState
          title="No settlements yet"
          description="Provider settlement batches will appear here after ingestion. Simulated files are labeled as simulated."
        />
      )}

      {canRead && list?.status === "success" && list.data.length > 0 && (
        <Table>
          <TableHead>
            <tr>
              <Th>Settlement</Th>
              <Th>Date</Th>
              <Th>Gross</Th>
              <Th>Provider fee</Th>
              <Th>POMPO fee</Th>
              <Th>Merchant net</Th>
              <Th>Status</Th>
            </tr>
          </TableHead>
          <TableBody>
            {list.data.map((row) => (
              <Tr key={row.id} onClick={() => setSelected(row)} className="cursor-pointer">
                <Td>
                  <MonoId>{row.public_identifier}</MonoId>
                  <div className="text-xs text-text-subtle">{row.provider_settlement_reference}</div>
                </Td>
                <Td>{row.settlement_date}</Td>
                <Td>{money(row.gross_amount)}</Td>
                <Td>{money(row.provider_fee)}</Td>
                <Td>{money(row.pompo_fee)}</Td>
                <Td>{money(row.merchant_net)}</Td>
                <Td>
                  <Badge tone={settlementTone(row.status)}>{row.status}</Badge>
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}

      <Modal
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `Settlement ${selected.public_identifier}` : "Settlement"}
      >
        {selected && (
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-text-subtle">POMPO reference</p>
              <p>{selected.payment_reference ?? "—"}</p>
            </div>
            <div>
              <p className="text-text-subtle">Provider reference</p>
              <p>{selected.provider_transaction_reference ?? selected.provider_settlement_reference}</p>
            </div>
            <div>
              <p className="text-text-subtle">Gross / net</p>
              <p>
                {money(selected.gross_amount)} → {money(selected.merchant_net)}
              </p>
            </div>
            <div>
              <p className="text-text-subtle">Reconciliation</p>
              <p>{selected.reconciliation?.status ?? "—"}</p>
              <p className="text-xs text-text-subtle">
                {selected.reconciliation?.mismatch_category ?? "No mismatch category"}
              </p>
            </div>
          </div>
        )}
      </Modal>
    </PageShell>
  );
}
