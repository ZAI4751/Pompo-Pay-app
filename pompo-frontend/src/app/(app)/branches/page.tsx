"use client";

import { useEffect, useState, type FormEvent } from "react";
import { GitBranch } from "lucide-react";
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
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Branch, Merchant } from "@/lib/types/merchant";
import type { ApiResult } from "@/lib/types/common";

export default function BranchesPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [merchantsResult, setMerchantsResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [merchantId, setMerchantId] = useState("");
  const [result, setResult] = useState<ApiResult<Branch[]> | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [name, setName] = useState("");
  const [address, setAddress] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deactivate, setDeactivate] = useState<Branch | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  useEffect(() => {
    void merchantsService.list().then((list) => {
      setMerchantsResult(list);
      if (list.status === "success" && list.data[0] && !merchantId) {
        setMerchantId(list.data[0].id);
      }
    });
    // merchantId is only used to seed the first selection.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!merchantId) return;
    let cancelled = false;
    void branchesService.list(merchantId).then((list) => {
      if (!cancelled) setResult(list);
    });
    return () => {
      cancelled = true;
    };
  }, [merchantId]);

  const merchants = merchantsResult?.status === "success" ? merchantsResult.data : [];
  const items = result?.status === "success" ? result.data : [];
  const canCreate = hasPermission("branches:create");
  const canDelete = hasPermission("branches:delete");

  async function onCreate(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const created = await branchesService.create(merchantId, { name, address: address || null });
    setSaving(false);
    if (created.status === "error") {
      setFormError(created.message);
      return;
    }
    setFormOpen(false);
    setName("");
    setAddress("");
    push("Branch created", "success");
    void branchesService.list(merchantId).then(setResult);
  }

  async function onDeactivate() {
    if (!deactivate) return;
    setDeactivating(true);
    const removed = await branchesService.remove(deactivate.id);
    setDeactivating(false);
    if (removed.status === "error") {
      push(removed.message, "error");
      return;
    }
    setDeactivate(null);
    push("Branch deactivated", "success");
    void branchesService.list(merchantId).then(setResult);
  }

  return (
    <PageShell
      title="Branches"
      breadcrumb={[{ label: "Business" }, { label: "Branches" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession && <MockDataBadge />}
          {canCreate && merchantId && (
            <Button size="sm" onClick={() => setFormOpen(true)}>
              New branch
            </Button>
          )}
        </div>
      }
    >
      <div className="mb-4 rounded-md border border-border bg-surface px-4 py-3">
        <label htmlFor="merchant-filter" className="text-sm font-medium text-text">
          Merchant
        </label>
        <select
          id="merchant-filter"
          className="mt-1.5 h-9 w-full max-w-sm rounded-sm border border-border-strong bg-surface px-3 text-sm text-text"
          value={merchantId}
          onChange={(event) => setMerchantId(event.target.value)}
        >
          {merchants.length === 0 && <option value="">No merchants</option>}
          {merchants.map((merchant) => (
            <option key={merchant.id} value={merchant.id}>
              {merchant.name}
            </option>
          ))}
        </select>
      </div>

      {merchantsResult?.status === "error" && (
        <ErrorState
          kind={merchantsResult.kind}
          description={merchantsResult.message}
          requestId={merchantsResult.requestId}
        />
      )}

      {merchantId && result === null && <TableSkeleton />}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={() => void branchesService.list(merchantId).then(setResult)}
        />
      )}

      {result?.status === "success" && items.length === 0 && (
        <EmptyState icon={GitBranch} title="No branches" description="Create a branch for this merchant." />
      )}

      {result?.status === "success" && items.length > 0 && (
        <Table>
          <TableHead>
            <Th>Branch</Th>
            <Th>ID</Th>
            <Th>Address</Th>
            <Th>Status</Th>
            <Th />
          </TableHead>
          <TableBody>
            {items.map((branch) => (
              <Tr key={branch.id}>
                <Td className="font-medium">{branch.name}</Td>
                <Td>
                  <MonoId>{branch.id}</MonoId>
                </Td>
                <Td className="text-text-muted">{branch.address ?? "—"}</Td>
                <Td>
                  <ActiveBadge isActive={branch.is_active} />
                </Td>
                <Td className="text-right">
                  {canDelete && branch.is_active && (
                    <Button variant="ghost" size="sm" onClick={() => setDeactivate(branch)}>
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
        title="New branch"
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
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Address" value={address} onChange={(e) => setAddress(e.target.value)} />
          {formError && <p className="text-sm text-error">{formError}</p>}
        </form>
      </Modal>

      <ConfirmationDialog
        open={Boolean(deactivate)}
        title="Deactivate branch"
        description="This is a soft-delete. The branch is marked inactive and excluded from normal reads."
        confirmLabel="Deactivate"
        destructive
        loading={deactivating}
        onConfirm={() => void onDeactivate()}
        onCancel={() => setDeactivate(null)}
      />
    </PageShell>
  );
}
