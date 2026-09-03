"use client";

import { useEffect, useMemo, useState } from "react";
import {
  Building2,
  HeartPulse,
  Landmark,
  LifeBuoy,
  Plug,
  Scale,
  Store,
  Users,
  Webhook,
} from "lucide-react";
import { PageShell } from "@/components/layout/PageShell";
import { MetricCard } from "@/components/ui/MetricCard";
import { Card, CardBody, CardEyebrow, CardHeader, CardTitle } from "@/components/ui/Card";
import { HealthBadge } from "@/components/ui/StatusBadge";
import { EmptyState } from "@/components/ui/EmptyState";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { MonoId } from "@/components/ui/Table";
import { HealthIndicator } from "@/components/ui/HealthIndicator";
import { MetricSkeleton } from "@/components/ui/SkeletonCard";
import { Stagger, StaggerItem } from "@/components/motion/Stagger";
import { Badge } from "@/components/ui/Badge";
import { merchantsService } from "@/lib/api/services/merchants";
import { branchesService } from "@/lib/api/services/branches";
import { healthService } from "@/lib/api/services/health";
import { paymentsService } from "@/lib/api/services/payments";
import { customersService, type CustomerStats } from "@/lib/api/services/customers";
import { webhooksService } from "@/lib/api/services/webhooks";
import { reconciliationService, settlementsService } from "@/lib/api/services/settlements";
import { USE_MOCKS } from "@/lib/api/config";
import { cn } from "@/lib/utils/cn";
import {
  isOperationalLiveRail,
  providerLifecycle,
  providerLifecycleTone,
} from "@/lib/providers/lifecycle";
import type { Merchant } from "@/lib/types/merchant";
import type { HealthResponse } from "@/lib/types/health";
import type { PaymentProvider } from "@/lib/types/payment";
import type { ReconciliationSummary, SettlementSummary } from "@/lib/types/settlement";

export default function DashboardPage() {
  const [merchants, setMerchants] = useState<Merchant[] | null>(null);
  const [branchTotal, setBranchTotal] = useState<number | null>(null);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [providers, setProviders] = useState<PaymentProvider[] | null>(null);
  const [customerStats, setCustomerStats] = useState<CustomerStats | null>(null);
  const [webhookFailures, setWebhookFailures] = useState<number | null>(null);
  const [webhookFailuresUnavailable, setWebhookFailuresUnavailable] = useState(false);
  const [reconSummary, setReconSummary] = useState<ReconciliationSummary | null>(null);
  const [settlementSummary, setSettlementSummary] = useState<SettlementSummary | null>(null);

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
        setBranchTotal(0);
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
    void webhooksService.list({ processing_status: "failed", limit: 50 }).then((result) => {
      if (result.status === "success") {
        setWebhookFailuresUnavailable(false);
        setWebhookFailures(result.data.length);
        return;
      }
      setWebhookFailures(null);
      setWebhookFailuresUnavailable(true);
    });
    void reconciliationService.summary().then((result) => {
      setReconSummary(result.status === "success" ? result.data : null);
    });
    void settlementsService.summary().then((result) => {
      setSettlementSummary(result.status === "success" ? result.data : null);
    });
  }, []);

  const merchantList = useMemo(() => merchants ?? [], [merchants]);
  const providerList = useMemo(() => providers ?? [], [providers]);
  const activeMerchants = merchantList.filter((merchant) => merchant.is_active).length;
  const liveRails = providerList.filter(isOperationalLiveRail).length;
  const contractPending = providerList.filter((provider) => providerLifecycle(provider) === "CONTRACT NOT READY").length;
  const pendingRequests = Object.values(customerStats?.payment_requests ?? {}).reduce((sum, count) => sum + count, 0);
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
        id: "live",
        label: "Live",
        tone: "bg-blue-500",
        count: providerList.filter((p) => providerLifecycle(p) === "LIVE").length,
      },
      {
        id: "sandbox",
        label: "Simulated",
        tone: "bg-emerald-500",
        count: providerList.filter((p) => providerLifecycle(p) === "SIMULATED").length,
      },
      {
        id: "contract",
        label: "Contract not ready",
        tone: "bg-slate-400",
        count: providerList.filter((p) => providerLifecycle(p) === "CONTRACT NOT READY").length,
      },
      {
        id: "blocked",
        label: "Disabled / unavailable",
        tone: "bg-orange-500",
        count: providerList.filter((p) => {
          const state = providerLifecycle(p);
          return state === "DISABLED" || state === "UNAVAILABLE" || state === "DEGRADED";
        }).length,
      },
    ];
    const total = Math.max(
      groups.reduce((sum, group) => sum + group.count, 0),
      1,
    );
    return groups.map((group) => ({ ...group, share: Math.round((group.count / total) * 100) }));
  }, [providerList]);

  return (
    <PageShell
      title="Dashboard"
      breadcrumb={[{ label: "Overview" }, { label: "Dashboard" }]}
      actions={USE_MOCKS ? <MockDataBadge /> : undefined}
    >
      <div className="mb-6 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-brand text-primary">Operations</p>
          <h2 className="mt-1 text-2xl font-semibold tracking-tight text-text sm:text-3xl">
            Payment control center
          </h2>
          <p className="mt-1 max-w-2xl text-sm text-text-muted">
            Counts come from live APIs. There is no global payment-volume telemetry for platform
            administrators, so this page does not invent a ledger or demo chart.
          </p>
        </div>
        <span className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs font-medium text-text-muted shadow-sm dark:bg-slate-900">
          <span
            className={cn("h-2 w-2 rounded-full", health?.status === "healthy" ? "bg-success" : "bg-warning")}
          />
          System {systemHeadline}
        </span>
      </div>

      <Stagger className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
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
              label="Live rails"
              value={`${liveRails}/${providerList.length}`}
              icon={Plug}
              hint={`${contractPending} awaiting contract`}
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
        <StaggerItem>
          {customerStats === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Open support"
              value={String(customerStats.support_open_count)}
              numericValue={customerStats.support_open_count}
              formatNumeric={(n) => String(Math.round(n))}
              icon={LifeBuoy}
              hint="GET /customers/stats"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {customerStats === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Payment requests"
              value={String(pendingRequests)}
              numericValue={pendingRequests}
              formatNumeric={(n) => String(Math.round(n))}
              icon={HeartPulse}
              hint="Counts by status from /customers/stats"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {webhookFailuresUnavailable ? (
            <MetricCard
              label="Failed webhooks"
              value="—"
              icon={Webhook}
              hint="Unavailable — GET /webhooks?processing_status=failed"
            />
          ) : webhookFailures === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Failed webhooks"
              value={String(webhookFailures)}
              numericValue={webhookFailures}
              formatNumeric={(n) => String(Math.round(n))}
              icon={Webhook}
              hint="GET /webhooks?processing_status=failed"
            />
          )}
        </StaggerItem>
        <StaggerItem>
          {reconSummary === null && settlementSummary === null ? (
            <MetricSkeleton />
          ) : (
            <MetricCard
              label="Recon exceptions"
              value={String((reconSummary?.discrepancy ?? 0) + (reconSummary?.unmatched ?? 0))}
              icon={Scale}
              hint={
                settlementSummary
                  ? `${settlementSummary.total_settlements} settlement rows`
                  : "GET /reconciliation/summary"
              }
            />
          )}
        </StaggerItem>
      </Stagger>

      <section className="mt-4 grid grid-cols-1 gap-4 xl:grid-cols-[minmax(0,1.2fr)_minmax(280px,0.8fr)]">
        <Card>
          <CardHeader>
            <div>
              <CardEyebrow>Financial control</CardEyebrow>
              <CardTitle className="mt-0.5">Settlements and reconciliation</CardTitle>
            </div>
          </CardHeader>
          <CardBody>
            {!reconSummary && !settlementSummary ? (
              <EmptyState
                title="No financial-control summary yet"
                description="Settlement batches and reconciliation exceptions appear after provider ingestion. Resolving a discrepancy does not rewrite the original payment."
              />
            ) : (
              <div className="grid gap-3 sm:grid-cols-2">
                <MiniStat
                  icon={Landmark}
                  label="Settlements"
                  value={String(settlementSummary?.total_settlements ?? 0)}
                />
                <MiniStat icon={Scale} label="Matched" value={String(reconSummary?.matched ?? 0)} />
                <MiniStat icon={Scale} label="Unmatched" value={String(reconSummary?.unmatched ?? 0)} />
                <MiniStat icon={Scale} label="Discrepancy" value={String(reconSummary?.discrepancy ?? 0)} />
              </div>
            )}
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
              providerList.map((provider) => {
                const lifecycle = providerLifecycle(provider);
                return (
                  <div
                    key={provider.code}
                    className="rounded-2xl border border-border bg-surface-inset/60 px-3.5 py-3"
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <p className="truncate text-sm font-semibold text-text" title={provider.display_name ?? provider.code}>
                          {provider.display_name ?? provider.code}
                        </p>
                        <MonoId>{provider.code}</MonoId>
                      </div>
                      <HealthIndicator
                        state={
                          lifecycle === "LIVE"
                            ? "active"
                            : lifecycle === "DEGRADED"
                              ? "degraded"
                              : lifecycle === "UNAVAILABLE"
                                ? "unavailable"
                                : "idle"
                        }
                        label={lifecycle}
                      />
                    </div>
                    <div className="mt-2">
                      <Badge tone={providerLifecycleTone(lifecycle)}>{lifecycle}</Badge>
                    </div>
                  </div>
                );
              })
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

      <section className="mt-4">
        <Card>
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
      </section>
    </PageShell>
  );
}

function MiniStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Landmark;
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-xl border border-border px-3 py-3">
      <p className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </p>
      <p className="mt-1 text-lg font-semibold tabular-nums text-text">{value}</p>
    </div>
  );
}
