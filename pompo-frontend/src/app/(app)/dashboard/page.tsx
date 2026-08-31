"use client";

import { useEffect, useState } from "react";
import { Store, Users, ArrowLeftRight, CheckCircle2, Server } from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardHeader, CardBody } from "@/components/ui/Card";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { StatusBadge } from "@/components/ui/StatusBadge";
import { Skeleton } from "@/components/ui/Skeleton";
import { transactionsService } from "@/lib/api/services/transactions";
import type { Transaction } from "@/lib/types/transaction";

export default function DashboardPage() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(null);

  useEffect(() => {
    void transactionsService.list().then((result) => {
      if (result.status === "success") setTransactions(result.data.items);
    });
  }, []);

  return (
    <PageShell title="Dashboard" breadcrumb={[{ label: "Dashboard" }]} actions={<MockDataBadge />}>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard label="Active Merchants" value="2" icon={Store} trend={{ value: "1 inactive", positive: false }} />
        <MetricCard label="Active Staff Users" value="171" icon={Users} trend={{ value: "+12 this week", positive: true }} />
        <MetricCard label="Transactions Today" value="3" icon={ArrowLeftRight} />
        <MetricCard label="Success Rate" value="66.7%" icon={CheckCircle2} trend={{ value: "-3.1% vs yesterday", positive: false }} />
      </div>

      <div className="mt-6 grid grid-cols-1 gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex items-center justify-between">
            <h2 className="text-sm font-semibold text-text">Recent Transactions</h2>
            <MockDataBadge />
          </CardHeader>
          <CardBody className="p-0">
            {transactions === null ? (
              <div className="p-4">
                <Skeleton className="mb-2 h-4 w-full" />
                <Skeleton className="mb-2 h-4 w-full" />
                <Skeleton className="h-4 w-full" />
              </div>
            ) : (
              <ul className="divide-y divide-border">
                {transactions.map((txn) => (
                  <li key={txn.id} className="flex items-center justify-between px-5 py-3 text-sm">
                    <div>
                      <p className="font-medium text-text">{txn.reference}</p>
                      <p className="text-text-muted">
                        {txn.merchant_name} &middot; {txn.currency} {txn.amount}
                      </p>
                    </div>
                    <StatusBadge status={txn.status} />
                  </li>
                ))}
              </ul>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <h2 className="text-sm font-semibold text-text">System Status</h2>
          </CardHeader>
          <CardBody className="space-y-3">
            {[
              { name: "Backend API", status: "Healthy" },
              { name: "PostgreSQL", status: "Healthy" },
              { name: "Redis", status: "Healthy" },
              { name: "Celery Worker", status: "Healthy" },
            ].map((service) => (
              <div key={service.name} className="flex items-center justify-between text-sm">
                <span className="flex items-center gap-2 text-text">
                  <Server className="h-3.5 w-3.5 text-text-subtle" aria-hidden="true" />
                  {service.name}
                </span>
                <span className="flex items-center gap-1.5 text-success">
                  <span className="h-1.5 w-1.5 rounded-full bg-success" />
                  {service.status}
                </span>
              </div>
            ))}
            <p className="pt-1 text-xs text-text-subtle">
              Illustrative status only -- wire to the real /health endpoints in a future iteration.
            </p>
          </CardBody>
        </Card>
      </div>
    </PageShell>
  );
}
