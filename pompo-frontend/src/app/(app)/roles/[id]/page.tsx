"use client";

import { useEffect, useState } from "react";
import { use } from "react";
import { Lock, ShieldCheck } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { Skeleton } from "@/components/ui/Skeleton";
import { usePermissions } from "@/lib/auth/usePermissions";
import { rolesService } from "@/lib/api/services/roles";
import type { RoleDetail } from "@/lib/types/rbac";
import type { ApiResult } from "@/lib/types/common";

export default function RoleDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { hasPermission } = usePermissions();
  const [result, setResult] = useState<ApiResult<RoleDetail> | null>(null);

  const load = () => {
    setResult(null);
    void rolesService.get(id).then(setResult);
  };

  useEffect(() => {
    void rolesService.get(id).then(setResult);
  }, [id]);

  const canManagePermissions = hasPermission("roles:update");

  return (
    <PageShell
      title="Role Detail"
      breadcrumb={[{ label: "Identity & Access" }, { label: "Roles", href: "/roles" }, { label: "Detail" }]}
      actions={<MockDataBadge />}
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
                  <Lock className="h-3 w-3" /> System role &mdash; not editable
                </Badge>
              )}
            </CardHeader>
            <CardBody>
              <p className="text-sm text-text-muted">{result.data.description}</p>
              <dl className="mt-4 grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
                <div>
                  <dt className="text-text-subtle">Users assigned</dt>
                  <dd className="font-medium text-text">{result.data.user_count}</dd>
                </div>
                <div>
                  <dt className="text-text-subtle">Permissions</dt>
                  <dd className="font-medium text-text">{result.data.permissions.length}</dd>
                </div>
              </dl>
            </CardBody>
          </Card>

          <Card>
            <CardHeader className="flex items-center justify-between">
              <h3 className="text-sm font-semibold text-text">Granted Permissions</h3>
              {!canManagePermissions && (
                <span className="text-xs text-text-subtle">
                  You need <code className="rounded bg-surface-raised px-1 py-0.5">roles:update</code> to modify grants
                </span>
              )}
            </CardHeader>
            <CardBody>
              <div className="flex flex-wrap gap-2">
                {result.data.permissions.map((permission) => (
                  <Badge key={permission.id} tone="neutral" title={permission.description ?? undefined}>
                    {permission.code}
                  </Badge>
                ))}
              </div>
            </CardBody>
          </Card>
        </div>
      )}
    </PageShell>
  );
}
