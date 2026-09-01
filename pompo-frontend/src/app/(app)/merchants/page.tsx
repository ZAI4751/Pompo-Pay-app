"use client";

import { useEffect, useRef, useState, type FormEvent } from "react";
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

type MerchantFormValues = typeof emptyForm;

export default function MerchantsPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [result, setResult] = useState<ApiResult<Merchant[]> | null>(null);
  const [query, setQuery] = useState("");
  const [formOpen, setFormOpen] = useState(false);
  const [editing, setEditing] = useState<Merchant | null>(null);
  const [formInitial, setFormInitial] = useState<MerchantFormValues>(emptyForm);
  const draftRef = useRef<MerchantFormValues>(emptyForm);
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
    setFormInitial(emptyForm);
    draftRef.current = emptyForm;
    setFormError(null);
    setFormOpen(true);
  }

  function openEdit(merchant: Merchant) {
    setEditing(merchant);
    const values = {
      name: merchant.name,
      legal_name: merchant.legal_name ?? "",
      registration_number: merchant.registration_number ?? "",
      contact_email: merchant.contact_email,
      contact_phone: merchant.contact_phone,
    };
    setFormInitial(values);
    draftRef.current = values;
    setFormError(null);
    setFormOpen(true);
  }

  async function onSave(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const draft = draftRef.current;
    const payload = {
      name: draft.name,
      legal_name: draft.legal_name || null,
      registration_number: draft.registration_number || null,
      contact_email: draft.contact_email,
      contact_phone: draft.contact_phone,
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
            <Th className="w-36" />
          </TableHead>
          <TableBody>
            {filtered.map((merchant) => (
              <Tr key={merchant.id}>
                <Td>
                  <p className="truncate font-medium text-text" title={merchant.name}>
                    {merchant.name}
                  </p>
                  <p className="truncate text-text-muted" title={merchant.legal_name ?? undefined}>
                    {merchant.legal_name}
                  </p>
                </Td>
                <Td>
                  <MonoId>{merchant.id}</MonoId>
                </Td>
                <Td>
                  <p className="truncate" title={merchant.contact_email}>
                    {merchant.contact_email}
                  </p>
                  <p className="truncate text-text-muted">{merchant.contact_phone}</p>
                </Td>
                <Td className="whitespace-normal">
                  <ActiveBadge isActive={merchant.is_active} />
                </Td>
                <Td className="max-w-none overflow-visible whitespace-nowrap text-right">
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
            <Button type="submit" form="merchant-editor" size="sm" loading={saving}>
              Save
            </Button>
          </>
        }
      >
        {formOpen && (
          <MerchantForm
            key={editing?.id ?? "new"}
            initial={formInitial}
            formError={formError}
            onChange={(values) => {
              draftRef.current = values;
            }}
            onSubmit={() => void onSave()}
          />
        )}
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

function MerchantForm({
  initial,
  formError,
  onChange,
  onSubmit,
}: {
  initial: MerchantFormValues;
  formError: string | null;
  onChange: (values: MerchantFormValues) => void;
  onSubmit: () => void;
}) {
  const [values, setValues] = useState(initial);

  function update<K extends keyof MerchantFormValues>(field: K, value: MerchantFormValues[K]) {
    const next = { ...values, [field]: value };
    setValues(next);
    onChange(next);
  }

  return (
    <form
      id="merchant-editor"
      className="space-y-4"
      onSubmit={(event) => {
        event.preventDefault();
        onSubmit();
      }}
    >
      <Input
        label="Name"
        required
        autoComplete="organization"
        value={values.name}
        onChange={(event) => update("name", event.target.value)}
      />
      <Input
        label="Legal name"
        autoComplete="organization"
        value={values.legal_name}
        onChange={(event) => update("legal_name", event.target.value)}
      />
      <Input
        label="Registration number"
        value={values.registration_number}
        onChange={(event) => update("registration_number", event.target.value)}
      />
      <Input
        label="Contact email"
        type="email"
        autoComplete="email"
        required
        value={values.contact_email}
        onChange={(event) => update("contact_email", event.target.value)}
      />
      <Input
        label="Contact phone"
        type="tel"
        autoComplete="tel"
        required
        value={values.contact_phone}
        onChange={(event) => update("contact_phone", event.target.value)}
      />
      {formError && <p className="text-sm text-error">{formError}</p>}
    </form>
  );
}
