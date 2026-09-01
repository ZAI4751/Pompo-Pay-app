"use client";

import { useEffect, useMemo, useState } from "react";
import { LayoutGroup, m } from "framer-motion";
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
  { id: "24h", label: "24h" },
  { id: "7d", label: "7d" },
  { id: "30d", label: "30d" },
];

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
      <section className="overflow-hidden rounded-md border border-primary/30 bg-dark-blue text-white glow-ring dark:shadow-luminous">
        <div className="relative px-5 py-6 sm:px-7 sm:py-7">
          <div className="pompo-grid-bg pointer-events-none absolute inset-0 opacity-30" aria-hidden="true" />
          <div className="pointer-events-none absolute -right-16 top-0 h-56 w-56 rounded-full bg-primary/20 blur-3xl" aria-hidden="true" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0 max-w-xl">
              <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">
                Pompo payment network
              </p>
              <h2 className="mt-2 text-3xl font-semibold tracking-tight">Operations control center</h2>
              <p className="mt-2 text-sm leading-relaxed text-white/70">
                Live merchant, health, and sandbox-provider state from the API. Volume charts are
                labeled mock series — they are not live settlement telemetry.
              </p>
            </div>
            <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
              <HeroStat label="System" value={systemHeadline} hint={health ? "GET /health" : "Waiting"} live={health?.status === "healthy"} />
              <HeroStat
                label="Providers"
                value={`${providers.length}`}
                hint="Catalog rails"
              />
              <HeroStat label="Volume" value={formatCompactMwk(totals.volume)} hint={`Illustrative ${period}`} />
              <HeroStat
                label="Success rate"
                value={`${totals.successRate.toFixed(1)}%`}
                hint="Mock window"
              />
            </div>
          </div>
        </div>
      </section>

      <Stagger className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <StaggerItem className="sm:col-span-2">
          <MetricCard
            label="Transaction volume"
            value={formatCompactMwk(totals.volume)}
            numericValue={totals.volume}
            formatNumeric={formatCompactMwk}
            icon={Wallet}
            emphasis="primary"
            series={series.map((point) => point.volume)}
            hint="Demo series — not live settlement"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Transaction count"
            value={formatCompactCount(totals.count)}
            numericValue={totals.count}
            formatNumeric={(n) => formatCompactCount(Math.round(n))}
            icon={ArrowLeftRight}
            series={series.map((point) => point.count)}
            hint="Push attempts in window"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Successful payments"
            value={formatCompactCount(totals.successful)}
            numericValue={totals.successful}
            formatNumeric={(n) => formatCompactCount(Math.round(n))}
            icon={CheckCircle2}
            hint={`${totals.successRate.toFixed(1)}% of window`}
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Failed payments"
            value={formatCompactCount(totals.failed)}
            numericValue={totals.failed}
            formatNumeric={(n) => formatCompactCount(Math.round(n))}
            icon={XCircle}
            hint="Includes timeouts in series"
          />
        </StaggerItem>
        <StaggerItem>
          <MetricCard
            label="Active merchants"
            value={String(activeMerchants)}
            numericValue={activeMerchants}
            formatNumeric={(n) => String(Math.round(n))}
            icon={Store}
            hint="GET /organization/merchants"
          />
        </StaggerItem>
        <StaggerItem>
          {branchTotal === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Active branches"
              value={String(branchTotal)}
              numericValue={branchTotal}
              formatNumeric={(n) => String(Math.round(n))}
              icon={Building2}
              hint="Sum of per-merchant branch lists"
            />
          )}
        </StaggerItem>
      </Stagger>

      <section className="mt-5 grid grid-cols-1 gap-4 xl:grid-cols-3">
        <Card className="xl:col-span-2" glow interactive>
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
            <div className="min-w-0 overflow-hidden">
              <TransactionAreaChart data={series} metric={metric} />
            </div>
            <div className="mt-2 flex items-center justify-between">
              <ChartLegend />
              <span className="text-[11px] text-text-subtle">Time ({period} buckets)</span>
            </div>
          </CardBody>
        </Card>

        <Card interactive>
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
        <Card className="xl:col-span-3" interactive>
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
                  className="rounded-sm border border-border bg-surface-inset/50 px-3.5 py-3 transition-colors duration-150 hover:border-primary/30"
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
                    {provider.capabilities.supports_status_query ? "yes" : "no"} · Cancel{" "}
                    {provider.capabilities.supports_cancel ? "yes" : "no"}
                  </p>
                </div>
              ))
            )}
          </CardBody>
        </Card>

        <Card className="xl:col-span-2" interactive>
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
                    className="flex min-w-0 items-center justify-between rounded-sm border border-border px-3 py-2.5"
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
        <Card interactive>
          <CardHeader>
            <div>
              <CardEyebrow>Recent activity</CardEyebrow>
              <CardTitle className="mt-0.5">Latest payment events</CardTitle>
            </div>
          </CardHeader>
          <CardBody className="p-0">
            {transactions === null ? (
              <div className="space-y-3 p-5">
                <MetricSkeleton />
              </div>
            ) : USE_MOCKS && transactions.length > 0 ? (
              <ActivityTimeline items={transactions} />
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

function HeroStat({
  label,
  value,
  hint,
  live,
}: {
  label: string;
  value: string;
  hint: string;
  live?: boolean;
}) {
  return (
    <div className="min-w-0 rounded-sm border border-white/10 bg-black/25 px-3 py-2.5 pompo-glass">
      <p className="truncate text-[10px] font-semibold uppercase tracking-[0.14em] text-white/50">{label}</p>
      <p className="mt-1 flex min-w-0 items-center gap-1.5 text-sm font-semibold tracking-tight">
        {live && (
          <span className="relative flex h-2 w-2 shrink-0" aria-hidden="true">
            <span className="absolute inset-0 rounded-full bg-success opacity-60 motion-safe:animate-ping" />
            <span className="relative h-2 w-2 rounded-full bg-success" />
          </span>
        )}
        <span className="truncate">{value}</span>
      </p>
      <p className="mt-0.5 truncate text-[10px] text-white/45">{hint}</p>
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
  const layoutKey = options.map((option) => option.id).join("-");
  return (
    <LayoutGroup id={`segmented-${layoutKey}`}>
      <div className="relative inline-flex rounded-sm border border-border bg-slate-50 p-0.5 dark:bg-slate-900">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onChange(option.id)}
          className={cn(
            "relative rounded-sm px-2.5 py-1 text-[11px] font-medium transition-colors duration-200",
            value === option.id ? "text-text" : "text-text-muted hover:text-text",
          )}
        >
          {value === option.id && (
            <m.span
              layoutId={`segmented-${layoutKey}`}
              className="absolute inset-0 rounded-sm bg-white shadow-sm dark:bg-slate-800"
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

