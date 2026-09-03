"use client";

import { useEffect, useState, type FormEvent } from "react";
import { QrCode } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { EmptyState } from "@/components/ui/EmptyState";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { tillsService } from "@/lib/api/services/tills";
import { qrService } from "@/lib/api/services/qr";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Branch, Merchant, Till } from "@/lib/types/merchant";
import type { QRCodeRecord } from "@/lib/types/qr";
import type { ApiResult } from "@/lib/types/common";

function qrStatusTone(status: string): "active" | "inactive" {
  return status === "active" ? "active" : "inactive";
}

export default function QRCodesPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();

  const [merchantsResult, setMerchantsResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [merchantId, setMerchantId] = useState("");
  const [branchesResult, setBranchesResult] = useState<ApiResult<Branch[]> | null>(null);
  const [branchId, setBranchId] = useState("");
  const [tillsResult, setTillsResult] = useState<ApiResult<Till[]> | null>(null);
  const [tillId, setTillId] = useState("");

  const [records, setRecords] = useState<QRCodeRecord[]>([]);
  const [dynamicOpen, setDynamicOpen] = useState(false);
  const [amount, setAmount] = useState("");
  const [saving, setSaving] = useState(false);
  const [revokeTarget, setRevokeTarget] = useState<QRCodeRecord | null>(null);
  const [revoking, setRevoking] = useState(false);
  const [lookupId, setLookupId] = useState("");
  const [lookupLoading, setLookupLoading] = useState(false);

  const canCreate = hasPermission("qr:create");
  const canRevoke = hasPermission("qr:revoke");
  const canRead = hasPermission("qr:read");

  useEffect(() => {
    void merchantsService.list().then((list) => {
      setMerchantsResult(list);
      if (list.status === "success" && list.data[0] && !merchantId) {
        setMerchantId(list.data[0].id);
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!merchantId) return;
    let cancelled = false;
    void branchesService.list(merchantId).then((list) => {
      if (cancelled) return;
      setBranchesResult(list);
      if (list.status === "success" && list.data[0]) {
        setBranchId(list.data[0].id);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  useEffect(() => {
    if (!branchId) return;
    let cancelled = false;
    void tillsService.list(branchId).then((list) => {
      if (cancelled) return;
      setTillsResult(list);
      if (list.status === "success" && list.data[0]) {
        setTillId(list.data[0].id);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [branchId]);

  const merchants = merchantsResult?.status === "success" ? merchantsResult.data : [];
  const branches = branchesResult?.status === "success" ? branchesResult.data : [];
  const tills = tillsResult?.status === "success" ? tillsResult.data : [];

  function upsertRecord(record: QRCodeRecord) {
    setRecords((prev) => {
      const idx = prev.findIndex((r) => r.public_identifier === record.public_identifier);
      if (idx >= 0) {
        const next = [...prev];
        next[idx] = record;
        return next;
      }
      return [record, ...prev];
    });
  }

  async function onCreateStatic() {
    if (!merchantId || !branchId || !tillId) return;
    setSaving(true);
    const created = await qrService.createStatic({
      merchant_id: merchantId,
      branch_id: branchId,
      till_id: tillId,
    });
    setSaving(false);
    if (created.status === "error") {
      push(created.message, "error");
      return;
    }
    upsertRecord(created.data);
    push("Static QR created", "success");
  }

  async function onCreateDynamic(event?: FormEvent) {
    event?.preventDefault();
    if (!merchantId || !branchId || !tillId || !amount) return;
    setSaving(true);
    const created = await qrService.createDynamic({
      merchant_id: merchantId,
      branch_id: branchId,
      till_id: tillId,
      amount,
      currency: "MWK",
      payment_method: "mobile_money",
      provider_code: "simulated",
      idempotency_key: `dyn-${Date.now()}`,
    });
    setSaving(false);
    if (created.status === "error") {
      push(created.message, "error");
      return;
    }
    upsertRecord(created.data);
    setDynamicOpen(false);
    setAmount("");
    push("Dynamic QR created", "success");
  }

  async function onLookup() {
    if (!lookupId.trim()) return;
    setLookupLoading(true);
    const result = canRead
      ? await qrService.getAdmin(lookupId.trim())
      : await qrService.inspect(lookupId.trim());
    setLookupLoading(false);
    if (result.status === "error") {
      push(result.message, "error");
      return;
    }
    if (canRead && "encoded_payload" in result.data) {
      upsertRecord(result.data as QRCodeRecord);
      push("QR loaded", "success");
    } else {
      push("QR inspect view loaded", "success");
    }
  }

  async function onRevoke() {
    if (!revokeTarget) return;
    setRevoking(true);
    const revoked = await qrService.revoke(revokeTarget.public_identifier);
    setRevoking(false);
    if (revoked.status === "error") {
      push(revoked.message, "error");
      return;
    }
    upsertRecord(revoked.data);
    setRevokeTarget(null);
    push("QR revoked", "success");
  }

  return (
    <PageShell
      title="QR Codes"
      breadcrumb={[{ label: "Payments" }, { label: "QR Codes" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession ? <MockDataBadge /> : null}
          {canCreate ? (
            <>
              <Button variant="secondary" disabled={saving || !tillId} onClick={() => void onCreateStatic()}>
                Create static QR
              </Button>
              <Button disabled={saving || !tillId} onClick={() => setDynamicOpen(true)}>
                Create dynamic QR
              </Button>
            </>
          ) : null}
        </div>
      }
    >
      <div className="mb-6 grid gap-4 md:grid-cols-3">
        <label className="flex flex-col gap-1 text-sm">
          Merchant
          <select
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
            value={merchantId}
            onChange={(e) => setMerchantId(e.target.value)}
          >
            {merchants.map((m) => (
              <option key={m.id} value={m.id}>
                {m.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Branch
          <select
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
            value={branchId}
            onChange={(e) => setBranchId(e.target.value)}
          >
            {branches.map((b) => (
              <option key={b.id} value={b.id}>
                {b.name}
              </option>
            ))}
          </select>
        </label>
        <label className="flex flex-col gap-1 text-sm">
          Till
          <select
            className="rounded-md border border-[var(--border)] bg-[var(--surface)] px-3 py-2"
            value={tillId}
            onChange={(e) => setTillId(e.target.value)}
          >
            {tills.map((t) => (
              <option key={t.id} value={t.id}>
                {t.name} ({t.code})
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mb-6 flex flex-wrap items-end gap-2">
        <Input
          label="Lookup by public ID"
          value={lookupId}
          onChange={(e) => setLookupId(e.target.value)}
          placeholder="QRABC123456789"
        />
        <Button variant="secondary" disabled={lookupLoading} onClick={() => void onLookup()}>
          Load QR
        </Button>
      </div>

      {records.length === 0 ? (
        <EmptyState
          icon={QrCode}
          title="No QR codes yet"
          description="Create a static till QR or a dynamic checkout QR for the selected context."
        />
      ) : (
        <Table>
          <TableHead>
            <tr>
              <Th>Public ID</Th>
              <Th>Type</Th>
              <Th>Status</Th>
              <Th>Merchant / Till</Th>
              <Th>Amount</Th>
              <Th>Payload</Th>
              <Th>Actions</Th>
            </tr>
          </TableHead>
          <TableBody>
            {records.map((qr) => (
              <Tr key={qr.public_identifier}>
                <Td>
                  <MonoId>{qr.public_identifier}</MonoId>
                </Td>
                <Td className="capitalize">{qr.qr_type}</Td>
                <Td>
                  <span className="inline-flex items-center gap-2">
                    <ActiveBadge isActive={qrStatusTone(qr.status) === "active"} />
                    <span className="text-xs text-[var(--muted)]">{qr.status}</span>
                  </span>
                </Td>
                <Td>
                  {qr.merchant_name} · {qr.till_name}
                </Td>
                <Td>
                  {qr.amount ? `${qr.amount} ${qr.currency}` : "—"}
                </Td>
                <Td>
                  <code className="block max-w-xs truncate text-xs">{qr.encoded_payload}</code>
                </Td>
                <Td>
                  {canRevoke && qr.status === "active" ? (
                    <Button variant="ghost" size="sm" onClick={() => setRevokeTarget(qr)}>
                      Revoke
                    </Button>
                  ) : null}
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}

      <Modal open={dynamicOpen} onClose={() => setDynamicOpen(false)} title="Create dynamic QR">
        <form onSubmit={(e) => void onCreateDynamic(e)} className="flex flex-col gap-4">
          <Input
            label="Amount (MWK)"
            type="text"
            inputMode="decimal"
            required
            value={amount}
            onChange={(e) => setAmount(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button type="button" variant="secondary" onClick={() => setDynamicOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={saving}>
              Create
            </Button>
          </div>
        </form>
      </Modal>

      <ConfirmationDialog
        open={revokeTarget !== null}
        title="Revoke QR code?"
        description={`Revoke ${revokeTarget?.public_identifier}? Scans will no longer accept this QR.`}
        confirmLabel="Revoke"
        loading={revoking}
        onConfirm={() => void onRevoke()}
        onCancel={() => setRevokeTarget(null)}
      />
    </PageShell>
  );
}
