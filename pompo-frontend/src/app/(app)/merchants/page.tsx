"use client";

import { useEffect, useState, type FormEvent } from "react";
import { Plus, Store } from "lucide-react";
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
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Merchant } from "@/lib/types/merchant";
import type { ApiResult } from "@/lib/types/common";

const emptyForm = {
  name: "",
  legal_name: "",
  registration_number: "",
  contact_email: "",
  contact_phone: "",
};

export default function MerchantsPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [result, setResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [query, setQuery] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Merchant | null>(null);
  const [form, setForm] = useState(emptyForm);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deactivate, setDeactivate] = useState<Merchant | null>(null);
  const [deactivating, setDeactivating] = useState(false);

  const load = () => {
    void merchantsService.list().then(setResult);
  };

  useEffect(() => {
    void merchantsService.list().then(setResult);
  }, []);

  const items = result?.status === "success" ? result.data : [];
  const filtered = items.filter((merchant) => merchant.name.toLowerCase().includes(query.toLowerCase()));
  const canCreate = hasPermission("merchants:create");
  const canUpdate = hasPermission("merchants:update");
  const canDelete = hasPermission("merchants:delete");

  function openCreate() {
    setEditing(null);
    setForm(emptyForm);
    setFormError(null);
    setFormOpen(true);
  }

  function openEdit(merchant: Merchant) {
    setEditing(merchant);
    setForm({
      name: merchant.name,
      legal_name: merchant.legal_name ?? "",
      registration_number: merchant.registration_number ?? "",
      contact_email: merchant.contact_email,
      contact_phone: merchant.contact_phone,
    });
    setFormError(null);
    setFormOpen(true);
  }

  async function onSave(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const payload = {
      name: form.name,
      legal_name: form.legal_name || null,
      registration_number: form.registration_number || null,
      contact_email: form.contact_email,
      contact_phone: form.contact_phone,
    };
    const saved = editing
      ? await merchantsService.update(editing.id, payload)
      : await merchantsService.create(payload);
    setSaving(false);
    if (saved.status === "error") {
      setFormError(saved.message);
      return;
    }
    setFormOpen(false);
    push(editing ? "Merchant updated" : "Merchant created", "success");
    load();
  }

  async function onDeactivate() {
    if (!deactivate) return;
    setDeactivating(true);
    const removed = await merchantsService.remove(deactivate.id);
    setDeactivating(false);
    if (removed.status === "error") {
      push(removed.message, "error");
      return;
    }
    setDeactivate(null);
    push("Merchant deactivated", "success");
    load();
  }

  return (
    <PageShell
      title="Merchants"
      breadcrumb={[{ label: "Business" }, { label: "Merchants" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession && <MockDataBadge />}
          {canCreate && (
            <Button size="sm" onClick={openCreate}>
              <Plus className="h-4 w-4" /> New Merchant
            </Button>
          )}
        </div>
      }
    >
      <div className="mb-4 flex flex-col gap-3 rounded-md border border-border bg-surface px-4 py-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="max-w-xs flex-1">
          <Input placeholder="Filter merchants" value={query} onChange={(e) => setQuery(e.target.value)} />
        </div>
        {result?.status === "success" && (
          <p className="text-xs text-text-muted">
            Showing {filtered.length} of {items.length}
          </p>
        )}
      </div>

      {result === null && <TableSkeleton />}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={load}
        />
      )}

      {result?.status === "success" && filtered.length === 0 && (
        <EmptyState
          icon={Store}
          title={query ? "No merchants match your search" : "No merchants yet"}
          description={query ? "Try a different search term." : "Merchants will appear here once onboarded."}
        />
      )}

      {result?.status === "success" && filtered.length > 0 && (
        <Table>
          <TableHead>
            <Th>Merchant</Th>
            <Th>ID</Th>
            <Th>Contact</Th>
            <Th>Status</Th>
            <Th />
          </TableHead>
          <TableBody>
            {filtered.map((merchant) => (
              <Tr key={merchant.id}>
                <Td>
                  <p className="font-medium text-text">{merchant.name}</p>
                  <p className="text-text-muted">{merchant.legal_name}</p>
                </Td>
                <Td>
                  <MonoId>{merchant.id}</MonoId>
                </Td>
                <Td>
                  <p>{merchant.contact_email}</p>
                  <p className="text-text-muted">{merchant.contact_phone}</p>
                </Td>
                <Td>
                  <ActiveBadge isActive={merchant.is_active} />
                </Td>
                <Td className="text-right">
                  {canUpdate && (
                    <Button variant="ghost" size="sm" onClick={() => openEdit(merchant)}>
                      Edit
                    </Button>
                  )}
                  {canDelete && merchant.is_active && (
                    <Button variant="ghost" size="sm" onClick={() => setDeactivate(merchant)}>
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
        title={editing ? "Edit merchant" : "New merchant"}
        footer={
          <>
            <Button variant="secondary" size="sm" onClick={() => setFormOpen(false)}>
              Cancel
            </Button>
            <Button size="sm" loading={saving} onClick={() => void onSave()}>
              Save
            </Button>
          </>
        }
      >
        <form className="space-y-3" onSubmit={onSave}>
          <Input label="Name" required value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} />
          <Input
            label="Legal name"
            value={form.legal_name}
            onChange={(e) => setForm({ ...form, legal_name: e.target.value })}
          />
          <Input
            label="Registration number"
            value={form.registration_number}
            onChange={(e) => setForm({ ...form, registration_number: e.target.value })}
          />
          <Input
            label="Contact email"
            type="email"
            required
            value={form.contact_email}
            onChange={(e) => setForm({ ...form, contact_email: e.target.value })}
          />
          <Input
            label="Contact phone"
            required
            value={form.contact_phone}
            onChange={(e) => setForm({ ...form, contact_phone: e.target.value })}
          />
          {formError && <p className="text-sm text-error">{formError}</p>}
        </form>
      </Modal>

      <ConfirmationDialog
        open={Boolean(deactivate)}
        title="Deactivate merchant"
        description="This is a soft-delete. The merchant is marked inactive and excluded from normal reads."
        confirmLabel="Deactivate"
        destructive
        loading={deactivating}
        onConfirm={() => void onDeactivate()}
        onCancel={() => setDeactivate(null)}
      />
    </PageShell>
  );
}
