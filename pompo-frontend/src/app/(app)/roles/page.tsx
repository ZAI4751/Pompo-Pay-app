"use client";

import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { ShieldCheck, Lock } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { Modal } from "@/components/ui/Modal";
import { ConfirmationDialog } from "@/components/ui/ConfirmationDialog";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { rolesService } from "@/lib/api/services/roles";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { Role } from "@/lib/types/rbac";
import type { ApiResult } from "@/lib/types/common";

export default function RolesPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [result, setResult] = useState<ApiResult<Role[]> | null>(null);
  const [formOpen, setFormOpen] = useState(false);
  const [code, setCode] = useState("");
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [removeRole, setRemoveRole] = useState<Role | null>(null);
  const [removing, setRemoving] = useState(false);

  const load = () => {
    void rolesService.list().then(setResult);
  };

  useEffect(() => {
    void rolesService.list().then(setResult);
  }, []);

  async function onCreate(event?: FormEvent) {
    event?.preventDefault();
    setSaving(true);
    setFormError(null);
    const created = await rolesService.create({
      code,
      name,
      description: description || null,
    });
    setSaving(false);
    if (created.status === "error") {
      setFormError(created.message);
      return;
    }
    setFormOpen(false);
    setCode("");
    setName("");
    setDescription("");
    push("Role created", "success");
    load();
  }

  async function onRemove() {
    if (!removeRole) return;
    setRemoving(true);
    const removed = await rolesService.remove(removeRole.id);
    setRemoving(false);
    if (removed.status === "error") {
      push(removed.message, "error");
      return;
    }
    setRemoveRole(null);
    push("Role deactivated", "success");
    load();
  }

  return (
    <PageShell
      title="Roles"
      breadcrumb={[{ label: "Identity & Access" }, { label: "Roles" }]}
      actions={
        <div className="flex items-center gap-2">
          {isDemoSession && <MockDataBadge />}
          {hasPermission("roles:create") && (
            <Button size="sm" onClick={() => setFormOpen(true)}>
              New custom role
            </Button>
          )}
        </div>
      }
    >
      {result === null && <TableSkeleton cols={5} />}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={load}
        />
      )}

      {result?.status === "success" && (
        <Table>
          <TableHead>
            <Th>Role</Th>
            <Th>Type</Th>
            <Th className="text-right">Permissions</Th>
            <Th>Status</Th>
            <Th className="w-36" />
          </TableHead>
          <TableBody>
            {result.data.map((role) => (
              <Tr key={role.id}>
                <Td>
                  <p className="flex min-w-0 items-center gap-1.5 font-medium text-text">
                    <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-text-subtle" aria-hidden="true" />
                    <span className="truncate" title={role.name}>
                      {role.name}
                    </span>
                  </p>
                  <p className="truncate text-text-muted" title={role.description ?? undefined}>
                    {role.description}
                  </p>
                  <MonoId>{role.code}</MonoId>
                </Td>
                <Td className="whitespace-normal">
                  {role.is_system_role ? (
                    <Badge tone="info" className="gap-1">
                      <Lock className="h-3 w-3" /> System
                    </Badge>
                  ) : (
                    <Badge tone="neutral">Custom</Badge>
                  )}
                </Td>
                <Td className="text-right tabular-nums">{role.permission_codes.length}</Td>
                <Td className="whitespace-normal">
                  <ActiveBadge isActive={role.is_active} />
                </Td>
                <Td className="max-w-none overflow-visible whitespace-nowrap text-right">
                  <Link href={`/roles/${role.id}`} className="text-sm font-medium text-primary hover:underline">
                    View
                  </Link>
                  {hasPermission("roles:delete") && !role.is_system_role && (
                    <Button variant="ghost" size="sm" className="ml-2" onClick={() => setRemoveRole(role)}>
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
        title="New custom role"
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
          <Input
            label="Code"
            hint="lowercase_with_underscores"
            required
            value={code}
            onChange={(e) => setCode(e.target.value)}
          />
          <Input label="Name" required value={name} onChange={(e) => setName(e.target.value)} />
          <Input label="Description" value={description} onChange={(e) => setDescription(e.target.value)} />
          {formError && <p className="text-sm text-error">{formError}</p>}
        </form>
      </Modal>

      <ConfirmationDialog
        open={Boolean(removeRole)}
        title="Deactivate custom role"
        description="System roles cannot be deactivated. This deactivates a custom role only."
        confirmLabel="Deactivate"
        destructive
        loading={removing}
        onConfirm={() => void onRemove()}
        onCancel={() => setRemoveRole(null)}
      />
    </PageShell>
  );
}
