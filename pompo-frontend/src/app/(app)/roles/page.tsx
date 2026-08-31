"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ShieldCheck, Lock } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { Badge } from "@/components/ui/Badge";
import { rolesService } from "@/lib/api/services/roles";
import type { Role } from "@/lib/types/rbac";
import type { ApiResult } from "@/lib/types/common";

export default function RolesPage() {
  const [result, setResult] = useState<ApiResult<Role[]> | null>(null);

  const load = () => {
    setResult(null);
    void rolesService.list().then(setResult);
  };

  useEffect(() => {
    void rolesService.list().then(setResult);
  }, []);

  return (
    <PageShell title="Roles" breadcrumb={[{ label: "Identity & Access" }, { label: "Roles" }]} actions={<MockDataBadge />}>
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
            <Th>Permissions</Th>
            <Th>Users</Th>
            <Th />
          </TableHead>
          <TableBody>
            {result.data.map((role) => (
              <Tr key={role.id}>
                <Td>
                  <p className="flex items-center gap-1.5 font-medium text-text">
                    <ShieldCheck className="h-3.5 w-3.5 text-text-subtle" aria-hidden="true" />
                    {role.name}
                  </p>
                  <p className="text-text-muted">{role.description}</p>
                </Td>
                <Td>
                  {role.is_system_role ? (
                    <Badge tone="info" className="gap-1">
                      <Lock className="h-3 w-3" /> System
                    </Badge>
                  ) : (
                    <Badge tone="neutral">Custom</Badge>
                  )}
                </Td>
                <Td>{role.permission_count}</Td>
                <Td>{role.user_count}</Td>
                <Td>
                  <Link href={`/roles/${role.id}`} className="text-sm font-medium text-primary hover:underline">
                    View
                  </Link>
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}
    </PageShell>
  );
}
