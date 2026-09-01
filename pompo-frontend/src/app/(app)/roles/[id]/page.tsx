"use client";

import { use, useEffect, useState } from "react";
import { Lock, ShieldCheck } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Button } from "@/components/ui/Button";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useAuth } from "@/lib/auth/AuthContext";
import { useToast } from "@/components/ui/Toast";
import { rolesService } from "@/lib/api/services/roles";
import { permissionsService } from "@/lib/api/services/permissions";
import type { Permission, RoleDetail } from "@/lib/types/rbac";
import type { ApiResult } from "@/lib/types/common";

export default function RoleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [result, setResult] = useState<ApiResult<RoleDetail> | null>(null);
  const [catalog, setCatalog] = useState<Permission[]>([]);
  const [busy, setBusy] = useState<string | null>(null);

  const load = () => {
    void rolesService.get(id).then(setResult);
    void permissionsService.list().then((list) => {
      if (list.status === "success") setCatalog(list.data);
    });
  };

  useEffect(() => {
    void rolesService.get(id).then(setResult);
    void permissionsService.list().then((list) => {
      if (list.status === "success") setCatalog(list.data);
    });
  }, [id]);

  const canGrant = hasPermission("role_permissions:grant");
  const canRevoke = hasPermission("role_permissions:revoke");

  async function grant(permission: Permission) {
    setBusy(permission.id);
    const granted = await rolesService.grantPermission(id, permission.id);
    setBusy(null);
    if (granted.status === "error") {
      push(granted.message, "error");
      return;
    }
    push(`Granted ${permission.code}`, "success");
    load();
  }

  async function revoke(permission: Permission) {
    setBusy(permission.id);
    const revoked = await rolesService.revokePermission(id, permission.id);
    setBusy(null);
    if (revoked.status === "error") {
      push(revoked.message, "error");
      return;
    }
    push(`Revoked ${permission.code}`, "success");
    load();
  }

  return (
    <PageShell
      title="Role Detail"
      breadcrumb={[{ label: "Identity & Access" }, { label: "Roles", href: "/roles" }, { label: "Detail" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      {result === null && (
        <Card>
          <CardBody>
            <Skeleton className="mb-3 h-6 w-48" />
            <Skeleton className="h-4 w-full" />
          </CardBody>
        </Card>
      )}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={load}
        />
      )}

      {result?.status === "success" && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <ShieldCheck className="h-5 w-5 text-primary" aria-hidden="true" />
                <div>
                  <h2 className="text-sm font-semibold text-text">{result.data.name}</h2>
                  <p className="text-xs text-text-muted">{result.data.code}</p>
                </div>
              </div>
              {result.data.is_system_role && (
                <Badge tone="info" className="gap-1">
                  <Lock className="h-3 w-3" /> System role — grants are locked
                </Badge>
              )}
            </CardHeader>
            <CardBody>
              <p className="text-sm text-text-muted">{result.data.description}</p>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-text-subtle">Permissions</dt>
                  <dd className="font-medium text-text">{result.data.permission_codes.length}</dd>
                </div>
                <div>
                  <dt className="text-text-subtle">Status</dt>
                  <dd className="font-medium text-text">{result.data.is_active ? "Active" : "Inactive"}</dd>
                </div>
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <h3 className="text-sm font-semibold text-text">Granted permissions</h3>
            </CardHeader>
            <CardBody>
              {result.data.permissions.length === 0 ? (
                <p className="text-sm text-text-muted">No permissions granted.</p>
              ) : (
                <div className="flex flex-wrap gap-2">
                  {result.data.permissions.map((permission) => (
                    <Badge key={permission.id} tone="neutral" title={permission.description ?? undefined}>
                      {permission.code}
                    </Badge>
                  ))}
                </div>
              )}
            </CardBody>
          </Card>

          {!result.data.is_system_role && catalog.length > 0 && (
            <Card>
              <CardHeader>
                <h3 className="text-sm font-semibold text-text">Catalog</h3>
                <p className="text-xs text-text-subtle">
                  Duplicate grants return 409. System-role mutations are rejected by the API.
                </p>
              </CardHeader>
              <CardBody className="space-y-2">
                {catalog.map((permission) => {
                  const granted = result.data.permission_codes.includes(permission.code);
                  return (
                    <div
                      key={permission.id}
                      className="flex items-center justify-between gap-3 rounded-sm border border-border px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium text-text">{permission.code}</p>
                        <p className="text-xs text-text-muted">{permission.description}</p>
                      </div>
                      {granted
                        ? canRevoke && (
                            <Button
                              variant="secondary"
                              size="sm"
                              loading={busy === permission.id}
                              onClick={() => void revoke(permission)}
                            >
                              Revoke
                            </Button>
                          )
                        : canGrant && (
                            <Button
                              size="sm"
                              loading={busy === permission.id}
                              onClick={() => void grant(permission)}
                            >
                              Grant
                            </Button>
                          )}
                    </div>
                  );
                })}
              </CardBody>
            </Card>
          )}
        </div>
      )}
    </PageShell>
  );
}
