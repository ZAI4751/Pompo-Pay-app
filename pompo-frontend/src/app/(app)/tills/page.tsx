"use client";

import { useEffect, useState, type FormEvent } from "react";
import { MonitorSmartphone } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { Modal } from "@/components/ui/Modal";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { tillsService } from "@/lib/api/services/tills";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Branch, Merchant, Till } from "@/lib/types/merchant";
import type { ApiResult } from "@/lib/types/common";

export default function TillsPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [merchantsResult, setMerchantsResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [merchantId, setMerchantId] = useState("");
  const [branchesResult, setBranchesResult] = useState<ApiResult<Branch[]> | null>(null);
  const [branchId, setBranchId] = useState("");
  const [result, setResult] = useState<ApiResult<Till[]> | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deactivate, setDeactivate] = useState<Till | null>(null);
  const [deactivating, setDeactivating] = useState(false);

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
      if (!cancelled) setResult(list);
    });
    return () => {
      cancelled = true;
    };
  }, [branchId]);

  const merchants = merchantsResult?.status === "success" ? merchantsResult.data : [];
  const branches = branchesResult?.status === "success" ? branchesResult.data : [];
  const items = result?.status === "success" ? result.data : [];
  const canCreate = hasPermission("tills:create");
  const canDelete = hasPermission("tills:delete");

  async function onCreate(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const created = await tillsService.create(branchId, { code, name });
    setSaving(false);
    if (created.status === "error") {
      setFormError(created.message);
      return;
    }
    setFormOpen(false);
    setCode("");
    setName("");
    push("Till created", "success");
    void tillsService.list(branchId).then(setResult);
  }

  async function onDeactivate() {
    if (!deactivate) return;
    setDeactivating(true);
    const removed = await tillsService.remove(deactivate.id);
    setDeactivating(false);
    if (removed.status === "error") {
      push(removed.message, "error");
      return;
    }
    setDeactivate(null);
    push("Till deactivated", "success");
    void tillsService.list(branchId).then(setResult);
  }

  return (
    <PageShell
      title="Tills"
      breadcrumb={[{ label: "Business" }, { label: "Tills" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession && <MockDataBadge />}
          {canCreate && (
            <Button size="sm" onClick={() => setFormOpen(true)} disabled={!branchId}>
              New till
            </Button>
          )}
        </div>
      }
    >
      <div className="mb-4 flex flex-col gap-3 sm:flex-row">
        <label className="text-sm text-text-muted">
          Merchant
          <select
            className="mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text"
            value={merchantId}
            onChange={(event) => {
              setMerchantId(event.target.value);
              setBranchId("");
              setBranchesResult(null);
              setResult(null);
            }}
          >
            {merchants.map((merchant) => (
              <option key={merchant.id} value={merchant.id}>
                {merchant.name}
              </option>
            ))}
          </select>
        </label>
        <label className="text-sm text-text-muted">
          Branch
          <select
            className="mt-1 block w-full rounded-sm border border-border bg-surface px-3 py-2 text-sm text-text"
            value={branchId}
            onChange={(event) => {
              setBranchId(event.target.value);
              setResult(null);
            }}
          >
            {branches.map((branch) => (
              <option key={branch.id} value={branch.id}>
                {branch.name}
              </option>
            ))}
          </select>
        </label>
      </div>

      {branchId && result === null && <TableSkeleton cols={4} />}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={() => void tillsService.list(branchId).then(setResult)}
        />
      )}

      {result?.status === "success" && items.length === 0 && (
        <EmptyState
          title="No tills"
          description="Create a till on this branch before taking payments."
          icon={MonitorSmartphone}
        />
      )}

      {result?.status === "success" && items.length > 0 && (
        <Table>
          <TableHead>
            <Th>Till</Th>
            <Th>Code</Th>
            <Th>Status</Th>
            <Th />
          </TableHead>
          <TableBody>
            {items.map((till) => (
              <Tr key={till.id}>
                <Td>
                  <p className="font-medium text-text">{till.name}</p>
                  <MonoId>{till.id}</MonoId>
                </Td>
                <Td className="font-mono text-sm">{till.code}</Td>
                <Td>
                  <ActiveBadge isActive={till.is_active} />
                </Td>
                <Td className="text-right">
                  {canDelete && (
                    <Button variant="ghost" size="sm" onClick={() => setDeactivate(till)}>
                      Deactivate
                    </Button>
                  )}
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}

      <Modal
        open={formOpen}
        onClose={() => setFormOpen(false)}
        title="New till"
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" loading={saving} onClick={() => void onCreate()}>
              Create
            </Button>
          </>
        }
      >
        <form className="space-y-3" onSubmit={onCreate}>
          <Input label="Code" required value={code} onChange={(e) => setCode(e.target.value)} />
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          {formError && <p className="text-sm text-error">{formError}</p>}
        </form>
      </Modal>

      <ConfirmationDialog
        open={Boolean(deactivate)}
        title="Deactivate till"
        description="The till stays on historical payments. It will no longer accept new checkouts."
        confirmLabel="Deactivate"
        destructive
        loading={deactivating}
        onConfirm={() => void onDeactivate()}
        onCancel={() => setDeactivate(null)}
      />
    </PageShell>
  );
}
