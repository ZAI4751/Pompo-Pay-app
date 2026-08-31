"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { ErrorState } from "@/components/ui/ErrorState";
import { rolesService } from "@/lib/api/services/roles";
import { mockPermissions } from "@/mocks/data";

export default function PermissionsPage() {
  const [ready, setReady] = useState(false);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    // Permissions are a fixed, code-defined catalog (see
    // pompo-backend/docs/decisions.md) -- not user-creatable -- so listing
    // them doesn't need its own network round trip in the mock layer, but
    // we still route through a service call shape (rolesService.list) to
    // keep the loading/error states real rather than instant.
    void rolesService
      .list()
      .then(() => setReady(true))
      .catch(() => setFailed(true));
  }, []);

  return (
    <PageShell
      title="Permissions"
      breadcrumb={[{ label: "Identity & Access" }, { label: "Permissions" }]}
      actions={<MockDataBadge />}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Permissions are a fixed catalog defined by the backend codebase (
        <code className="rounded bg-surface-raised px-1 py-0.5">resource:action</code>), not
        arbitrary strings admins can invent. This prevents privilege escalation via permission
        injection -- see the backend&apos;s docs/decisions.md.
      </p>

      {!ready && !failed && <TableSkeleton cols={2} />}
      {failed && <ErrorState kind="network" />}

      {ready && (
        <Table>
          <TableHead>
            <Th>Code</Th>
            <Th>Description</Th>
          </TableHead>
          <TableBody>
            {mockPermissions.map((permission) => (
              <Tr key={permission.id}>
                <Td>
                  <code className="text-sm font-medium text-text">{permission.code}</code>
                </Td>
                <Td className="text-text-muted">{permission.description}</Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}
    </PageShell>
  );
}
