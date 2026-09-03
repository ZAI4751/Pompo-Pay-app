"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { Modal } from "@/components/ui/Modal";
import { webhooksService } from "@/lib/api/services/webhooks";
import { usePermissions } from "@/lib/auth/usePermissions";
import type { WebhookEventRecord } from "@/lib/types/webhook";
import type { ApiResult } from "@/lib/types/common";

function statusTone(status: string): "active" | "inactive" {
  if (status === "processed" || status === "duplicate") return "active";
  if (status === "failed" || status === "rejected" || status === "reconciliation") return "inactive";
  return "inactive";
}

export default function WebhooksPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("webhooks:read");
  const [result, setResult] = useState<ApiResult<WebhookEventRecord[]> | null>(null);
  const [selected, setSelected] = useState<WebhookEventRecord | null>(null);

  useEffect(() => {
    if (!canRead) return;
    void webhooksService.list({ limit: 50 }).then(setResult);
  }, [canRead]);

  return (
    <PageShell title="Webhooks" breadcrumb={[{ label: "Integrations" }, { label: "Webhooks" }]}>
      {!canRead && (
        <ErrorState kind="forbidden" description="You do not have permission to view webhook events." />
      )}

      {canRead && result === null && (
        <div className="grid gap-3">
          <SkeletonCard />
          <SkeletonCard />
        </div>
      )}

      {canRead && result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
        />
      )}

      {canRead && result?.status === "success" && result.data.length === 0 && (
        <EmptyState
          title="No webhook events yet"
          description="Inbound provider callbacks will appear here after ingestion."
        />
      )}

      {canRead && result?.status === "success" && result.data.length > 0 && (
        <Table>
          <TableHead>
            <tr>
              <Th>Event</Th>
              <Th>Type</Th>
              <Th>Payment</Th>
              <Th>Received</Th>
              <Th>Status</Th>
              <Th>Retries</Th>
              <Th>Signature</Th>
              <Th>Failure</Th>
            </tr>
          </TableHead>
          <TableBody>
            {result.data.map((event) => (
              <Tr key={event.id} onClick={() => setSelected(event)} className="cursor-pointer">
                <Td>
                  <MonoId>{event.public_identifier}</MonoId>
                  <div className="text-xs text-text-subtle">{event.provider_event_id}</div>
                </Td>
                <Td>{event.event_type}</Td>
                <Td>{event.payment_reference ?? "—"}</Td>
                <Td>{new Date(event.received_at).toLocaleString()}</Td>
                <Td>
                  <ActiveBadge isActive={statusTone(event.processing_status) === "active"} />
                  <span className="ml-2 capitalize">{event.processing_status}</span>
                </Td>
                <Td>{event.processing_attempts}</Td>
                <Td>{event.signature_verified ? "verified" : "unverified"}</Td>
                <Td>{event.failure_category ?? "—"}</Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}

      <Modal
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `Webhook ${selected.public_identifier}` : "Webhook event"}
      >
        {selected && (
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-text-subtle">Processing status</p>
              <p>{selected.processing_status}</p>
            </div>
            <div>
              <p className="text-text-subtle">Failure category</p>
              <p>{selected.failure_category ?? "—"}</p>
            </div>
            <div>
              <p className="text-text-subtle">Failure code</p>
              <p>{selected.failure_code ?? "—"}</p>
            </div>
            <div>
              <p className="text-text-subtle">Signature / timestamp</p>
              <p>
                {selected.signature_verified ? "Signature verified" : "Signature unverified"} ·{" "}
                {selected.timestamp_validated ? "timestamp valid" : "timestamp not validated"}
              </p>
            </div>
            <div>
              <p className="text-text-subtle">Processed at</p>
              <p>{selected.processed_at ? new Date(selected.processed_at).toLocaleString() : "—"}</p>
            </div>
            <p className="text-xs text-text-subtle">
              Raw webhook payloads are withheld in this console so secrets cannot leak.
            </p>
          </div>
        )}
      </Modal>
    </PageShell>
  );
}
