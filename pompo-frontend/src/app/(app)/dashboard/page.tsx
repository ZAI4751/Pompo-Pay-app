"use client";

import { useEffect, useMemo, useState } from "react";
import { LayoutGroup, m } from "framer-motion";
import {
  ArrowLeftRight,
  Building2,
  CheckCircle2,
  Plug,
  Store,
  Users,
  Wallet,
  XCircle,
} from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardBody, CardEyebrow, CardHeader, CardTitle } from "@/components/ui/Card";
import { HealthBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { MonoId } from "@/components/ui/Table";
import { HealthIndicator } from "@/components/ui/HealthIndicator";
import { ActivityTimeline } from "@/components/ui/ActivityTimeline";
import { MetricSkeleton } from "@/components/ui/SkeletonCard";
import { Stagger, StaggerItem } from "@/components/motion/Stagger";
import { ChartLegend, TransactionAreaChart } from "@/components/charts/TransactionAreaChart";
import { RadialMeter } from "@/components/charts/RadialMeter";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { healthService } from "@/lib/api/services/health";
import { paymentsService } from "@/lib/api/services/payments";
import { customersService, type CustomerStats } from "@/lib/api/services/customers";
import { transactionsService } from "@/lib/api/services/transactions";
import { USE_MOCKS } from "@/lib/api/config";
import { formatCompactCount, formatCompactMwk } from "@/lib/format/money";
import { cn } from "@/lib/utils/cn";
import type { Transaction } from "@/lib/types/transaction";
import type { Merchant } from "@/lib/types/merchant";
import type { HealthResponse } from "@/lib/types/health";
import type { PaymentProvider } from "@/lib/types/payment";
import { mockVolumeSeries, type OpsPeriod } from "@/mocks/data";

const periods: { id: OpsPeriod; label: string }[] = [
  { id: "24h", label: "Last 24h" },
  { id: "7d", label: "Last 7 days" },
  { id: "30d", label: "Last 30 days" },
];

export default function DashboardPage() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(USE_MOCKS ? null : []);
  const [merchants, setMerchants] = useState<Merchant[] | null>(null);
  const [branchTotal, setBranchTotal] = useState<number | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providers, setProviders] = useState<PaymentProvider[] | null>(null);
  const [customerStats, setCustomerStats] = useState<CustomerStats | null>(null);
  const [period, setPeriod] = useState<OpsPeriod>("7d");
  const [metric, setMetric] = useState<"volume" | "count">("volume");

  useEffect(() => {
    void merchantsService.list().then((result) => {
      if (result.status === "success") {
        setMerchants(result.data);
        void Promise.all(result.data.map((merchant) => branchesService.list(merchant.id))).then(
          (branchResults) => {
            const total = branchResults.reduce(
              (sum, item) => sum + (item.status === "success" ? item.data.length : 0),
              0,
            );
            setBranchTotal(total);
          },
        );
      } else {
        setMerchants([]);
      }
    });
    void healthService.check().then((result) => {
      if (result.status === "success") setHealth(result.data);
    });
    void paymentsService.listProviders().then((result) => {
      setProviders(result.status === "success" ? result.data : []);
    });
    void customersService.stats().then((result) => {
      setCustomerStats(
        result.status === "success"
          ? result.data
          : { customer_count: 0, payment_requests: {}, support_open_count: 0 },
      );
    });
    if (USE_MOCKS) {
      void transactionsService.list().then((result) => {
        setTransactions(result.status === "success" ? result.data.items : []);
      });
    }
  }, []);

  const series = mockVolumeSeries[period];
  const totals = useMemo(() => {
    const volume = series.reduce((sum, point) => sum + point.volume, 0);
    const count = series.reduce((sum, point) => sum + point.count, 0);
    const failed = series.reduce((sum, point) => sum + point.failed, 0);
    const successful = Math.max(count - failed, 0);
    const successRate = count === 0 ? 0 : (successful / count) * 100;
    return { volume, count, failed, successful, successRate };
  }, [series]);

  const merchantList = merchants ?? [];
  const providerList = providers ?? [];
  const activeMerchants = merchantList.filter((merchant) => merchant.is_active).length;
  const liveProviders = providerList.filter((provider) => provider.is_active).length;
  const systemHeadline = health
    ? health.status === "healthy"
      ? "Healthy"
      : health.status === "degraded"
        ? "Degraded"
        : health.status
    : "Checking";

  const railMix = useMemo(() => {
    const groups = [
      {
        id: "active",
        label: "Active rails",
        tone: "bg-blue-500",
        count: providerList.filter((p) => p.is_active && p.health_state === "active").length,
      },
      {
        id: "sandbox",
        label: "Sandbox",
        tone: "bg-emerald-500",
        count: providerList.filter((p) => p.is_simulated).length,
      },
      {
        id: "blocked",
        label: "Disabled / down",
        tone: "bg-orange-500",
        count: providerList.filter((p) => !p.is_active || p.health_state === "unavailable").length,
      },
    ];
    const total = Math.max(
      groups.reduce((sum, group) => sum + group.count, 0),
      1,
    );
    return groups.map((group) => ({ ...group, share: Math.round((group.count / total) * 100) }));
  }, [providerList]);

  return (
    <PageShell title="Dashboard" breadcrumb={[{ label: "Overview" }, { label: "Dashboard" }]}>
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Operations</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text sm:text-3xl">
            Payment control center
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-text-muted">
            Merchant, rail, and platform health from the live API. Volume charts remain labeled demo
            series until a settlement telemetry endpoint exists.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs font-medium text-text-muted shadow-sm dark:bg-slate-900">
            <span
              className={cn(
                "h-2 w-2 rounded-full",
                health?.status === "healthy" ? "bg-success" : "bg-warning",
              )}
            />
            System {systemHeadline}
          </span>
          <Segmented options={periods} value={period} onChange={setPeriod} />
        </div>
      </div>

      <Stagger className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StaggerItem>
          <MetricCard
            label="Transaction volume"
            value={formatCompactMwk(totals.volume)}
            numericValue={totals.volume}
            formatNumeric={formatCompactMwk}
            icon={Wallet}
            emphasis="primary"
            series={series.map((point) => point.volume)}
            hint={`Demo series · ${period}`}
          />
        </StaggerItem>
        <StaggerItem>
          {merchants === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Active merchants"
              value={String(activeMerchants)}
              numericValue={activeMerchants}
              formatNumeric={(n) => String(Math.round(n))}
              icon={Store}
              hint="GET /organization/merchants"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {providers === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Live providers"
              value={`${liveProviders}/${providerList.length}`}
              icon={Plug}
              hint="GET /payments/providers"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {customerStats === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Customers"
              value={String(customerStats.customer_count)}
              numericValue={customerStats.customer_count}
              formatNumeric={(n) => String(Math.round(n))}
              icon={Users}
              hint="GET /customers/stats"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {branchTotal === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Branches"
              value={String(branchTotal)}
              numericValue={branchTotal}
              formatNumeric={(n) => String(Math.round(n))}
              icon={Building2}
              hint="Sum of merchant branch lists"
            />
          )}
        </StaggerItem>
      </Stagger>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.65fr)_minmax(280px,0.8fr)]">
        <Card glow>
          <CardHeader>
            <div>
              <CardEyebrow>Activity</CardEyebrow>
              <CardTitle className="mt-0.5">Volume and failures</CardTitle>
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <MockDataBadge />
              <Segmented
                options={[
                  { id: "volume", label: "Volume" },
                  { id: "count", label: "Count" },
                ]}
                value={metric}
                onChange={setMetric}
              />
            </div>
          </CardHeader>
          <CardBody>
            <div className="mb-4 flex flex-wrap items-end justify-between gap-3">
              <div>
                <p className="text-3xl font-semibold tabular-nums text-text">
                  {metric === "volume" ? formatCompactMwk(totals.volume) : formatCompactCount(totals.count)}
                </p>
                <p className="mt-1 text-xs text-text-subtle">
                  {metric === "volume" ? "Settled volume (MWK)" : "Transaction count"} · dashed line is
                  failed attempts
                </p>
              </div>
              <div className="flex gap-4 text-xs text-text-muted">
                <span className="inline-flex items-center gap-1.5">
                  <ArrowLeftRight className="h-3.5 w-3.5" /> Window {period}
                </span>
                <span className="inline-flex items-center gap-1.5 text-error">
                  <XCircle className="h-3.5 w-3.5" /> {formatCompactCount(totals.failed)} failed
                </span>
              </div>
            </div>
            <TransactionAreaChart data={series} metric={metric} />
            <div className="mt-2">
              <ChartLegend />
            </div>
          </CardBody>
        </Card>

        <div className="space-y-4">
          <Card>
            <CardHeader>
              <div>
                <CardEyebrow>Quality</CardEyebrow>
                <CardTitle className="mt-0.5">Window success</CardTitle>
              </div>
              <MockDataBadge />
            </CardHeader>
            <CardBody className="flex flex-col gap-4">
              <RadialMeter
                value={totals.successRate}
                label="Success rate"
                caption={`${formatCompactCount(totals.failed)} failed of ${formatCompactCount(totals.count)}`}
              />
              <div className="grid grid-cols-2 gap-3 border-t border-border pt-4">
                <MiniStat icon={CheckCircle2} label="Settled" value={formatCompactCount(totals.successful)} />
                <MiniStat icon={XCircle} label="Failed" value={formatCompactCount(totals.failed)} />
              </div>
            </CardBody>
          </Card>

          <Card>
            <CardHeader>
              <div>
                <CardEyebrow>Rails</CardEyebrow>
                <CardTitle className="mt-0.5">Provider mix</CardTitle>
              </div>
            </CardHeader>
            <CardBody className="space-y-4">
              {providers === null ? (
                <MetricSkeleton />
              ) : providerList.length === 0 ? (
                <p className="text-sm text-text-muted">No providers returned. Seed the catalog or grant providers:read.</p>
              ) : (
                railMix.map((group) => (
                  <div key={group.id}>
                    <div className="flex items-center justify-between text-sm">
                      <span className="text-text-muted">{group.label}</span>
                      <span className="font-semibold tabular-nums text-text">{group.count}</span>
                    </div>
                    <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-surface-inset">
                      <div className={cn("h-full rounded-full", group.tone)} style={{ width: `${group.share}%` }} />
                    </div>
                  </div>
                ))
              )}
            </CardBody>
          </Card>
        </div>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader>
            <div>
              <CardEyebrow>Network</CardEyebrow>
              <CardTitle className="mt-0.5">Rail health</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="grid gap-3 sm:grid-cols-2">
            {providers === null ? (
              <MetricSkeleton />
            ) : providerList.length === 0 ? (
              <p className="text-sm text-text-muted">No provider catalog rows.</p>
            ) : (
              providerList.map((provider) => (
                <div
                  key={provider.code}
                  className="rounded-2xl border border-border bg-surface-inset/60 px-3.5 py-3 transition-colors hover:border-primary/30"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="truncate text-sm font-semibold text-text" title={provider.display_name ?? provider.code}>
                        {provider.display_name ?? provider.code}
                      </p>
                      <MonoId>
                        {provider.code}
                        {provider.is_simulated ? " · simulated" : ""}
                      </MonoId>
                    </div>
                    <HealthIndicator
                      state={
                        !provider.is_active
                          ? "idle"
                          : provider.health_state === "degraded"
                            ? "degraded"
                            : provider.health_state === "unavailable"
                              ? "unavailable"
                              : provider.health_state === "active"
                                ? "active"
                                : "idle"
                      }
                      label={provider.is_simulated ? "Sandbox" : provider.environment}
                    />
                  </div>
                  <p className="mt-2 text-[11px] text-text-subtle">
                    Push {provider.capabilities.supports_push_payment ? "yes" : "no"} · Status{" "}
                    {provider.capabilities.supports_status_query ? "yes" : "no"} · QR{" "}
                    {provider.capabilities.supports_qr ? "yes" : "no"}
                  </p>
                </div>
              ))
            )}
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <div>
              <CardEyebrow>Platform</CardEyebrow>
              <CardTitle className="mt-0.5">System nodes</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="space-y-2.5">
            {health ? (
              Object.entries(health.components).map(([name, component]) => (
                <div
                  key={name}
                  className="flex min-w-0 items-center justify-between rounded-2xl border border-border px-3 py-2.5"
                >
                  <div className="min-w-0">
                    <p className="truncate text-sm font-medium capitalize text-text">{name}</p>
                    <p className="text-[11px] text-text-subtle">{component.status}</p>
                  </div>
                  <HealthBadge
                    state={
                      component.healthy ? "healthy" : component.status === "unknown" ? "unknown" : "down"
                    }
                  />
                </div>
              ))
            ) : (
              <p className="text-sm text-text-muted">Waiting for GET /health.</p>
            )}
          </CardBody>
        </Card>
      </section>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader>
            <div>
              <CardEyebrow>Business</CardEyebrow>
              <CardTitle className="mt-0.5">Merchants</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {merchants === null ? (
              <div className="p-5">
                <MetricSkeleton />
              </div>
            ) : merchantList.length === 0 ? (
              <div className="p-5">
                <EmptyState title="No merchants" description="Create a merchant to populate this roster." />
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full text-left text-sm">
                  <thead className="text-[11px] font-semibold uppercase tracking-[0.12em] text-text-subtle">
                    <tr>
                      <th className="px-5 py-2 font-semibold">Merchant</th>
                      <th className="px-5 py-2 font-semibold">Contact</th>
                      <th className="px-5 py-2 font-semibold">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {merchantList.map((merchant) => (
                      <tr key={merchant.id} className="border-t border-border/70 hover:bg-primary-light/40">
                        <td className="px-5 py-3">
                          <p className="font-semibold text-text">{merchant.name}</p>
                          <p className="text-xs text-text-subtle">{merchant.legal_name ?? merchant.id}</p>
                        </td>
                        <td className="px-5 py-3 text-text-muted">
                          <p>{merchant.contact_email}</p>
                          <p className="text-xs">{merchant.contact_phone}</p>
                        </td>
                        <td className="px-5 py-3">
                          <span
                            className={cn(
                              "rounded-full px-2.5 py-1 text-xs font-semibold",
                              merchant.is_active ? "bg-success-bg text-success" : "bg-surface-inset text-text-muted",
                            )}
                          >
                            {merchant.is_active ? "Active" : "Inactive"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <div>
              <CardEyebrow>Recent activity</CardEyebrow>
              <CardTitle className="mt-0.5">Latest payments</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {transactions === null ? (
              <div className="p-5">
                <MetricSkeleton />
              </div>
            ) : USE_MOCKS && transactions.length > 0 ? (
              <ActivityTimeline items={transactions} />
            ) : (
              <div className="p-5">
                <EmptyState
                  title="No payment list API"
                  description="Look up a payment by reference on Payments. This panel will not invent a ledger."
                />
              </div>
            )}
          </CardBody>
        </Card>
      </section>
    </PageShell>
  );
}

function MiniStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof CheckCircle2;
  label: string;
  value: string;
}) {
  return (
    <div>
      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-text">{value}</p>
    </div>
  );
}

function Segmented<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { id: T; label: string }[];
  value: T;
  onChange: (next: T) => void;
}) {
  const layoutKey = options.map((option) => option.id).join("-");
  return (
    <LayoutGroup id={`segmented-${layoutKey}`}>
      <div className="relative inline-flex rounded-full border border-border bg-white p-1 dark:bg-slate-900">
        {options.map((option) => (
          <button
            key={option.id}
            type="button"
            onClick={() => onChange(option.id)}
            className={cn(
              "relative rounded-full px-3 py-1.5 text-[11px] font-medium transition-colors duration-200",
              value === option.id ? "text-text" : "text-text-muted hover:text-text",
            )}
          >
            {value === option.id && (
              <m.span
                layoutId={`segmented-${layoutKey}`}
                className="absolute inset-0 rounded-full bg-primary-light"
                transition={{ type: "spring", stiffness: 400, damping: 28 }}
              />
            )}
            <span className="relative z-10">{option.label}</span>
          </button>
        ))}
      </div>
    </LayoutGroup>
  );
}
