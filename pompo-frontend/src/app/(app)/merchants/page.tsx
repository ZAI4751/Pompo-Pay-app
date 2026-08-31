"use client";

import { useEffect, useState } from "react";
import { Plus, Store } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Table, TableHead, Th, TableBody, Tr, Td } from "@/components/ui/Table";
import { TableSkeleton } from "@/components/ui/Skeleton";
import { EmptyState } from "@/components/ui/EmptyState";
import { ErrorState } from "@/components/ui/ErrorState";
import { ActiveBadge } from "@/components/ui/StatusBadge";
import { Input } from "@/components/ui/Input";
import { Button } from "@/components/ui/Button";
import { merchantsService } from "@/lib/api/services/merchants";
import type { Merchant } from "@/lib/types/merchant";
import type { ApiResult } from "@/lib/types/common";

export default function MerchantsPage() {
  const [result, setResult] = useState<ApiResult<{ items: Merchant[] }> | null>(null);
  const [query, setQuery] = useState("");

  const load = () => {
    setResult(null);
    void merchantsService.list().then(setResult);
  };

  useEffect(() => {
    void merchantsService.list().then(setResult);
  }, []);

  const items = result?.status === "success" ? result.data.items : [];
  const filtered = items.filter((m) => m.name.toLowerCase().includes(query.toLowerCase()));

  return (
    <PageShell
      title="Merchants"
      breadcrumb={[{ label: "Merchants" }]}
      actions={
        <div className="flex items-center gap-2">
          <MockDataBadge />
          <Button size="sm">
            <Plus className="h-4 w-4" /> New Merchant
          </Button>
        </div>
      }
    >
      <div className="mb-4 max-w-xs">
        <Input
          placeholder="Search merchants..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
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
            <Th>Contact</Th>
            <Th>Branches</Th>
            <Th>Status</Th>
          </TableHead>
          <TableBody>
            {filtered.map((merchant) => (
              <Tr key={merchant.id}>
                <Td>
                  <p className="font-medium text-text">{merchant.name}</p>
                  <p className="text-text-muted">{merchant.legal_name}</p>
                </Td>
                <Td>
                  <p>{merchant.contact_email}</p>
                  <p className="text-text-muted">{merchant.contact_phone}</p>
                </Td>
                <Td>{merchant.branch_count}</Td>
                <Td>
                  <ActiveBadge isActive={merchant.is_active} />
                </Td>
              </Tr>
            ))}
          </TableBody>
        </Table>
      )}
    </PageShell>
  );
}
