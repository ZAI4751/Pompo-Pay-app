"use client";

import { useEffect, useState } from "react";
import { Users as UsersIcon } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { Badge } from "@/components/ui/Badge";
import { usersService } from "@/lib/api/services/users";
import type { StaffUser } from "@/lib/types/staff-user";
import type { ApiResult } from "@/lib/types/common";

function formatRelative(iso: string | null): string {
  if (!iso) return "Never";
  const date = new Date(iso);
  return date.toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

export default function UsersPage() {
  const [result, setResult] = useState<ApiResult<{ items: StaffUser[] }> | null>(null);

  const load = () => {
    setResult(null);
    void usersService.list().then(setResult);
  };

  useEffect(() => {
    void usersService.list().then(setResult);
  }, []);

  return (
    <PageShell title="Users" breadcrumb={[{ label: "Identity & Access" }, { label: "Users" }]} actions={<MockDataBadge />}>
      {result === null && <TableSkeleton cols={6} />}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={load}
        />
      )}

      {result?.status === "success" && result.data.items.length === 0 && (
        <EmptyState icon={UsersIcon} title="No staff users yet" />
      )}

      {result?.status === "success" && result.data.items.length > 0 && (
        <Table>
          <TableHead>
            <Th>Name</Th>
            <Th>Role</Th>
            <Th>Merchant</Th>
            <Th>Branch</Th>
            <Th>Last Login</Th>
            <Th>Status</Th>
          </TableHead>
          <TableBody>
            {result.data.items.map((user) => (
              <Tr key={user.id}>
                <Td>
                  <p className="font-medium text-text">{user.full_name}</p>
                  <p className="text-text-muted">{user.email}</p>
                </Td>
                <Td>
                  <Badge tone="primary">{user.role_name}</Badge>
                </Td>
                <Td>{user.merchant_name ?? <span className="text-text-subtle">Platform-wide</span>}</Td>
                <Td>{user.branch_name ?? <span className="text-text-subtle">&mdash;</span>}</Td>
                <Td className="text-text-muted">{formatRelative(user.last_login_at)}</Td>
                <Td>
                  <ActiveBadge isActive={user.is_active} />
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}
    </PageShell>
  );
}
