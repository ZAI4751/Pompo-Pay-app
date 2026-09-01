"use client";

import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeftRight,
  Building2,
  CheckCircle2,
  Store,
  Wallet,
  XCircle,
} from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardBody, CardEyebrow, CardHeader, CardTitle } from "@/components/ui/Card";
import { StatusBadge, HealthBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { MonoId } from "@/components/ui/Table";
import { ChartLegend, TransactionAreaChart } from "@/components/charts/TransactionAreaChart";
import { RadialMeter } from "@/components/charts/RadialMeter";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { healthService } from "@/lib/api/services/health";
import { paymentsService } from "@/lib/api/services/payments";
import { transactionsService } from "@/lib/api/services/transactions";
import { USE_MOCKS } from "@/lib/api/config";
import { formatCompactCount, formatCompactMwk, formatMwk } from "@/lib/format/money";
import { cn } from "@/lib/utils/cn";
import type { Transaction } from "@/lib/types/transaction";
import type { Merchant } from "@/lib/types/merchant";
import type { HealthResponse } from "@/lib/types/health";
import type { PaymentProvider } from "@/lib/types/payment";
import { mockVolumeSeries, type OpsPeriod } from "@/mocks/data";

const periods: { id: OpsPeriod; label: string }[] = [
  { id: "24h", label: "24h" },
  { id: "7d", label: "7d" },
  { id: "30d", label: "30d" },
];

function formatStamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function DashboardPage() {
  const [transactions, setTransactions] = useState<Transaction[] | null>(USE_MOCKS ? null : []);
  const [merchants, setMerchants] = useState<Merchant[]>([]);
  const [branchTotal, setBranchTotal] = useState<number | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providers, setProviders] = useState<PaymentProvider[]>([]);
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
      }
    });
    void healthService.check().then((result) => {
      if (result.status === "success") setHealth(result.data);
    });
    void paymentsService.listProviders().then((result) => {
      if (result.status === "success") setProviders(result.data);
    });
    if (USE_MOCKS) {
      void transactionsService.list().then((result) => {
        if (result.status === "success") setTransactions(result.data.items);
        else setTransactions([]);
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

  const activeMerchants = merchants.filter((merchant) => merchant.is_active).length;
  const systemHeadline = health
    ? health.status === "healthy"
      ? "Healthy"
      : health.status === "degraded"
        ? "Degraded"
        : health.status
    : "Checking";

  return (
    <PageShell title="Dashboard" breadcrumb={[{ label: "Overview" }, { label: "Dashboard" }]}>
      <section className="overflow-hidden rounded-md border border-primary/25 bg-dark-blue text-white glow-ring">
        <div className="relative px-5 py-5 sm:px-6">
          <div className="pompo-grid-bg pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
          <div className="relative flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
            <div>
              <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">
                Pompo system overview
              </p>
              <h2 className="mt-1 text-2xl font-semibold tracking-tight">Platform operations at a glance</h2>
              <p className="mt-1.5 max-w-xl text-sm text-white/70">
                Merchant counts, health, and sandbox providers come from the live API. Volume and
                success-rate charts are labeled mock series — there is no ledger list endpoint.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <HeroStat label="System" value={systemHeadline} hint={health ? "GET /health" : "Waiting"} />
              <HeroStat
                label="Providers"
                value={`${providers.length} sandbox`}
                hint="Not live Airtel/TNM"
              />
              <HeroStat label="Volume" value={formatCompactMwk(totals.volume)} hint={`Window ${period}`} />
              <HeroStat
                label="Success rate"
                value={`${totals.successRate.toFixed(1)}%`}
                hint={`${formatCompactCount(totals.successful)} settled`}
              />
            </div>
          </div>
        </div>
      </section>

      <section className="mt-5 grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <div className="sm:col-span-2">
          <MetricCard
            label="Transaction volume"
            value={formatCompactMwk(totals.volume)}
            icon={Wallet}
            emphasis="primary"
            series={series.map((point) => point.volume)}
            hint="Demo series — not live settlement"
          />
        </div>
        <MetricCard
          label="Transaction count"
          value={formatCompactCount(totals.count)}
          icon={ArrowLeftRight}
          series={series.map((point) => point.count)}
          hint="Push attempts in window"
        />
        <MetricCard
          label="Successful payments"
          value={formatCompactCount(totals.successful)}
          icon={CheckCircle2}
          hint={`${totals.successRate.toFixed(1)}% of window`}
        />
        <MetricCard
          label="Failed payments"
          value={formatCompactCount(totals.failed)}
          icon={XCircle}
          hint="Includes timeouts in series"
        />
        <MetricCard
          label="Active merchants"
          value={String(activeMerchants)}
          icon={Store}
          hint="GET /organization/merchants"
        />
        <MetricCard
          label="Active branches"
          value={branchTotal === null ? "—" : String(branchTotal)}
          icon={Building2}
          hint="Sum of per-merchant branch lists"
        />
      </section>

      <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" glow>
          <CardHeader>
            <div>
              <CardEyebrow>Transaction activity</CardEyebrow>
              <CardTitle className="mt-0.5">Volume and failure trend</CardTitle>
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
              <Segmented
                options={periods}
                value={period}
                onChange={setPeriod}
              />
            </div>
          </CardHeader>
          <CardBody>
            <p className="mb-3 text-xs text-text-subtle">
              {metric === "volume" ? "Settled volume (MWK)" : "Transaction count"} · dashed line is
              failed attempts · source: mock ops series · window {period}
            </p>
            <TransactionAreaChart data={series} metric={metric} />
            <div className="mt-2 flex items-center justify-between">
              <ChartLegend />
              <span className="text-[11px] text-text-subtle">Time ({period} buckets)</span>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <div>
              <CardEyebrow>Quality</CardEyebrow>
              <CardTitle className="mt-0.5">Window success</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="flex flex-col gap-5">
            <RadialMeter
              value={totals.successRate}
              label="Success rate"
              caption={`${formatCompactCount(totals.failed)} failed of ${formatCompactCount(totals.count)} in ${period}`}
            />
            <div className="grid grid-cols-2 gap-3 border-t border-border pt-4">
              <MiniStat label="Settled" value={formatCompactCount(totals.successful)} />
              <MiniStat label="Failed" value={formatCompactCount(totals.failed)} />
            </div>
            <p className="text-[11px] text-text-subtle">
              Derived from the same illustrative series as the chart. Not a live provider SLA.
            </p>
          </CardBody>
        </Card>
      </section>

      <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-5">
        <Card className="xl:col-span-3">
          <CardHeader>
            <div>
              <CardEyebrow>Payment network</CardEyebrow>
              <CardTitle className="mt-0.5">Rail health</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="grid gap-3 sm:grid-cols-2">
            {providers.length === 0 ? (
              <p className="text-sm text-text-muted">
                No providers returned. Seed the catalog or grant providers:read.
              </p>
            ) : (
              providers.map((provider) => (
                <div
                  key={provider.code}
                  className="rounded-sm border border-border bg-surface-inset/50 px-3.5 py-3"
                >
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <p className="text-sm font-semibold text-text">
                        {provider.display_name ?? provider.code}
                      </p>
                      <MonoId>
                        {provider.code}
                        {provider.is_simulated ? " · simulated" : ""}
                      </MonoId>
                    </div>
                    <RailBadge status={provider.is_active ? "sandbox" : "degraded"} />
                  </div>
                  <p className="mt-2 text-[11px] text-text-subtle">
                    Push {provider.capabilities.supports_push_payment ? "yes" : "no"} · Status{" "}
                    {provider.capabilities.supports_status_query ? "yes" : "no"} · Cancel{" "}
                    {provider.capabilities.supports_cancel ? "yes" : "no"}
                  </p>
                </div>
              ))
            )}
          </CardBody>
        </Card>

        <Card className="xl:col-span-2">
          <CardHeader>
            <div>
              <CardEyebrow>System health</CardEyebrow>
              <CardTitle className="mt-0.5">Platform nodes</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="space-y-2.5">
            {health
              ? Object.entries(health.components).map(([name, component]) => (
                  <div
                    key={name}
                    className="flex items-center justify-between rounded-sm border border-border px-3 py-2.5"
                  >
                    <div>
                      <p className="text-sm font-medium capitalize text-text">{name}</p>
                      <p className="text-[11px] text-text-subtle">{component.status}</p>
                    </div>
                    <HealthBadge
                      state={
                        component.healthy ? "healthy" : component.status === "unknown" ? "unknown" : "down"
                      }
                    />
                  </div>
                ))
              : (
                  <p className="text-sm text-text-muted">Waiting for GET /health.</p>
                )}
            <p className="pt-1 text-[11px] text-text-subtle">
              Source: GET /api/v1/health. A 503 still returns this payload when the platform is degraded.
            </p>
          </CardBody>
        </Card>
      </section>

      <section className="mt-5">
        <Card>
          <CardHeader>
            <div>
              <CardEyebrow>Recent activity</CardEyebrow>
              <CardTitle className="mt-0.5">Latest payment events</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {transactions === null ? (
              <div className="p-5 text-sm text-text-muted">Loading…</div>
            ) : USE_MOCKS && transactions.length > 0 ? (
              <ul className="divide-y divide-border">
                {transactions.map((txn) => (
                  <li
                    key={txn.id}
                    className="flex flex-col gap-2 px-5 py-3.5 sm:flex-row sm:items-center sm:justify-between"
                  >
                    <div className="min-w-0">
                      <p className="font-medium text-text">{txn.merchant_name}</p>
                      <p className="mt-0.5 text-xs text-text-muted">
                        <MonoId>{txn.reference}</MonoId>
                        <span className="mx-1.5 text-text-subtle">·</span>
                        {txn.provider_name ?? "Unrouted"}
                        <span className="mx-1.5 text-text-subtle">·</span>
                        {formatStamp(txn.created_at)}
                      </p>
                    </div>
                    <div className="flex items-center gap-3">
                      <p className="text-sm font-semibold tabular-nums text-text">{formatMwk(txn.amount)}</p>
                      <StatusBadge status={txn.status} />
                    </div>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="p-5">
                <EmptyState
                  title="No payment list API"
                  description="Retrieve a payment by reference on Payments. This panel will not invent a ledger."
                />
              </div>
            )}
          </CardBody>
        </Card>
      </section>
    </PageShell>
  );
}

function HeroStat({ label, value, hint }: { label: string; value: string; hint: string }) {
  return (
    <div className="min-w-[8.5rem] rounded-sm border border-white/10 bg-black/20 px-3 py-2.5">
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-white/50">{label}</p>
      <p className="mt-1 text-sm font-semibold tracking-tight">{value}</p>
      <p className="mt-0.5 text-[10px] text-white/45">{hint}</p>
    </div>
  );
}

function MiniStat({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-[10px] font-semibold uppercase tracking-[0.14em] text-text-subtle">{label}</p>
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
  return (
    <div className="inline-flex rounded-sm border border-border bg-surface-inset p-0.5">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onChange(option.id)}
          className={cn(
            "rounded-sm px-2.5 py-1 text-[11px] font-medium transition-colors duration-150",
            value === option.id
              ? "bg-surface text-text"
              : "text-text-muted hover:text-text",
          )}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

function RailBadge({ status }: { status: "operational" | "degraded" | "sandbox" }) {
  const map = {
    operational: { label: "Operational", className: "bg-success-bg text-success" },
    degraded: { label: "Degraded", className: "bg-warning-bg text-warning" },
    sandbox: { label: "Sandbox", className: "bg-info-bg text-info" },
  };
  const { label, className } = map[status];
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide", className)}>
      {label}
    </span>
  );
}
