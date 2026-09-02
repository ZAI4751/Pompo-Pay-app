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
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { reconciliationService } from "@/lib/api/services/settlements";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import { formatMwk } from "@/lib/format/money";
import type { ReconciliationRecord, ReconciliationSummary } from "@/lib/types/settlement";
import type { ApiResult } from "@/lib/types/common";

function money(value: string | number | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return formatMwk(value);
}

function reconTone(status: string): "success" | "warning" | "error" | "info" | "neutral" {
  if (status === "matched" || status === "resolved") return "success";
  if (status === "partial_match" || status === "investigation") return "warning";
  if (status === "discrepancy" || status === "unmatched") return "error";
  return "neutral";
}

export default function ReconciliationPage() {
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const canRead = hasPermission("reconciliation:read");
  const canResolve = hasPermission("reconciliation:update");
  const [list, setList] = useState<ApiResult<ReconciliationRecord[]> | null>(null);
  const [summary, setSummary] = useState<ApiResult<ReconciliationSummary> | null>(null);
  const [selected, setSelected] = useState<ReconciliationRecord | null>(null);
  const [note, setNote] = useState("");
  const [saving, setSaving] = useState(false);

  function reload() {
    void reconciliationService.list({ limit: 50 }).then(setList);
    void reconciliationService.summary().then(setSummary);
  }

  useEffect(() => {
    if (!canRead) return;
    reload();
  }, [canRead]);

  async function resolve() {
    if (!selected) return;
    setSaving(true);
    const result = await reconciliationService.resolve(selected.id, note.trim());
    setSaving(false);
    if (result.status === "success") {
      push("Resolution recorded. Payment amounts were not changed.", "success");
      setSelected(result.data);
      setNote("");
      reload();
    } else {
      push(result.message, "error");
    }
  }

  return (
    <PageShell
      title="Reconciliation"
      breadcrumb={[{ label: "Operations" }, { label: "Reconciliation" }]}
    >
      {!canRead && (
        <ErrorState
          kind="forbidden"
          description="You do not have permission to view reconciliation."
        />
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
        <div className="mb-6 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
          <Card>
            <CardBody>
              <CardEyebrow>Matched rate</CardEyebrow>
              <CardTitle>{summary.data.matched_rate}%</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Unmatched</CardEyebrow>
              <CardTitle>{summary.data.unmatched_count}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Discrepancy total</CardEyebrow>
              <CardTitle>{money(summary.data.discrepancy_total)}</CardTitle>
            </CardBody>
          </Card>
          <Card>
            <CardBody>
              <CardEyebrow>Investigation</CardEyebrow>
              <CardTitle>{summary.data.investigation}</CardTitle>
            </CardBody>
          </Card>
        </div>
      )}

      {canRead && list?.status === "error" && (
        <ErrorState kind={list.kind} description={list.message} requestId={list.requestId} />
      )}

      {canRead && list?.status === "success" && list.data.length === 0 && (
        <EmptyState
          title="No reconciliation records"
          description="Records appear after settlement ingestion. Discrepancies are preserved; payments are never rewritten."
        />
      )}

      {canRead && list?.status === "success" && list.data.length > 0 && (
        <Table>
          <TableHead>
            <tr>
              <Th>Record</Th>
              <Th>POMPO ref</Th>
              <Th>Expected</Th>
              <Th>Actual</Th>
              <Th>Variance</Th>
              <Th>Status</Th>
            </tr>
          </TableHead>
          <TableBody>
            {list.data.map((row) => (
              <Tr key={row.id} onClick={() => setSelected(row)} className="cursor-pointer">
                <Td>
                  <MonoId>{row.public_identifier}</MonoId>
                  <div className="text-xs text-text-subtle">{row.mismatch_category ?? "matched"}</div>
                </Td>
                <Td>{row.pompo_reference ?? "—"}</Td>
                <Td>{money(row.expected_amount)}</Td>
                <Td>{money(row.actual_amount)}</Td>
                <Td>{money(row.variance)}</Td>
                <Td>
                  <Badge tone={reconTone(row.status)}>{row.status.replace("_", " ")}</Badge>
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}

      <Modal
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `Reconciliation ${selected.public_identifier}` : "Reconciliation"}
        footer={
          selected && canResolve && selected.status !== "resolved" ? (
            <Button onClick={() => void resolve()} loading={saving} disabled={!note.trim()}>
              Record resolution
            </Button>
          ) : undefined
        }
      >
        {selected && (
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-text-subtle">POMPO reference</p>
              <p>{selected.pompo_reference ?? "—"}</p>
            </div>
            <div>
              <p className="text-text-subtle">Provider reference</p>
              <p>{selected.provider_reference ?? "—"}</p>
            </div>
            <div>
              <p className="text-text-subtle">Expected vs actual</p>
              <p>
                {money(selected.expected_amount)} / {money(selected.actual_amount)} (variance{" "}
                {money(selected.variance)})
              </p>
            </div>
            <div>
              <p className="text-text-subtle">Fees (expected / actual)</p>
              <p>
                Provider {money(selected.expected_provider_fee)} / {money(selected.actual_provider_fee)}
              </p>
              <p>
                POMPO {money(selected.expected_pompo_fee)} / {money(selected.actual_pompo_fee)}
              </p>
            </div>
            <div>
              <p className="text-text-subtle">Detected</p>
              <p>{new Date(selected.detected_at).toLocaleString()}</p>
            </div>
            <div>
              <p className="text-text-subtle">Resolution</p>
              <p>{selected.resolution_note ?? selected.status}</p>
            </div>
            {canResolve && selected.status !== "resolved" && (
              <Input
                label="Resolution note"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="Document the investigation outcome. This does not change payment amounts."
              />
            )}
          </div>
        )}
      </Modal>
    </PageShell>
  );
}
