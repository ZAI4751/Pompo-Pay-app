"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td, MonoId } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { permissionsService } from "@/lib/api/services/permissions";
import { useAuth } from "@/lib/auth/AuthContext";
import type { Permission } from "@/lib/types/rbac";
import type { ApiResult } from "@/lib/types/common";

export default function PermissionsPage() {
  const { isDemoSession } = useAuth();
  const [result, setResult] = useState<ApiResult<Permission[]> | null>(null);

  const load = () => {
    void permissionsService.list().then(setResult);
  };

  useEffect(() => {
    void permissionsService.list().then(setResult);
  }, []);

  return (
    <PageShell
      title="Permissions"
      breadcrumb={[{ label: "Organization" }, { label: "Permissions" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Permissions are an immutable catalog (
        <code className="rounded bg-surface-raised px-1 py-0.5">resource:action</code>
        ). There is no create/update/delete API.
      </p>

      {result === null && <TableSkeleton cols={2} />}
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
            <Th>Code</Th>
            <Th>Description</Th>
          </TableHead>
          <TableBody>
            {result.data.map((permission) => (
              <Tr key={permission.id}>
                <Td>
                  <MonoId>{permission.code}</MonoId>
                </Td>
                <Td className="truncate text-text-muted" title={permission.description ?? undefined}>
                  {permission.description}
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}
    </PageShell>
  );
}
