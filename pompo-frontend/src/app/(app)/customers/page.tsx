"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { LifeBuoy, Send, Users } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { BackendUnavailable } from "@/components/ui/ComingSoon";
import { ErrorState } from "@/components/ui/ErrorState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { customersService, type CustomerStats } from "@/lib/api/services/customers";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import type { ApiResult } from "@/lib/types/common";

export default function CustomersPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const [stats, setStats] = useState<ApiResult<CustomerStats> | null>(null);

  useEffect(() => {
    void customersService.stats().then(setStats);
  }, []);

  const requestCounts = stats?.status === "success" ? stats.data.payment_requests : {};
  const requestTotal = Object.values(requestCounts).reduce((sum, count) => sum + count, 0);

  return (
    <PageShell
      title="Customers"
      breadcrumb={[{ label: "Organization" }, { label: "Customers" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Platform totals from GET /customers/stats. There is no customer directory API, so this
        page does not invent a staff-style customer list.
      </p>

      {stats?.status === "error" && (
        <ErrorState kind={stats.kind} description={stats.message} requestId={stats.requestId} />
      )}

      {stats?.status === "success" && (
        <div className="mb-4 grid gap-3 sm:grid-cols-3">
          <MetricCard
            label="Registered customers"
            value={String(stats.data.customer_count)}
            icon={Users}
            numericValue={stats.data.customer_count}
          />
          <MetricCard
            label="Payment requests"
            value={String(requestTotal)}
            icon={Send}
            numericValue={requestTotal}
            hint={Object.entries(requestCounts)
              .map(([status, count]) => `${status}: ${count}`)
              .join(" · ") || "No payment requests recorded"}
          />
          <MetricCard
            label="Open support"
            value={String(stats.data.support_open_count)}
            icon={LifeBuoy}
            numericValue={stats.data.support_open_count}
          />
        </div>
      )}

      <Card className="mb-4">
        <CardHeader>
          <CardTitle>Operational links</CardTitle>
        </CardHeader>
        <CardBody className="flex flex-wrap gap-3 text-sm">
          {hasPermission("users:read") ? (
            <Link className="text-primary underline" href="/support">
              Support requests
            </Link>
          ) : null}
          {hasPermission("transactions:read") ? (
            <Link className="text-primary underline" href="/payments">
              Payments
            </Link>
          ) : null}
        </CardBody>
      </Card>

      <BackendUnavailable
        feature="Customer directory"
        detail="The backend exposes register, profile, preferences, favorites, insights, and platform stats. It does not expose GET /customers as a searchable directory. This console will not fabricate customer records."
      />
    </PageShell>
  );
}
