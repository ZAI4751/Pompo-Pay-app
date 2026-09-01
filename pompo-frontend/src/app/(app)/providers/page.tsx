"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { Skeleton } from "@/components/ui/Skeleton";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { paymentsService } from "@/lib/api/services/payments";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { useToast } from "@/components/ui/Toast";
import type { PaymentProvider } from "@/lib/types/payment";
import type { ApiResult } from "@/lib/types/common";

export default function ProvidersPage() {
  const { isDemoSession } = useAuth();
  const { hasPermission } = usePermissions();
  const { push } = useToast();
  const [result, setResult] = useState<ApiResult<PaymentProvider[]> | null>(null);
  const [updating, setUpdating] = useState<string | null>(null);
  const canUpdate = hasPermission("providers:update");

  const load = () => {
    void paymentsService.listProviders().then(setResult);
  };

  useEffect(() => {
    void paymentsService.listProviders().then(setResult);
  }, []);

  async function toggleActive(provider: PaymentProvider) {
    setUpdating(provider.code);
    const updated = await paymentsService.updateProvider(provider.code, {
      is_active: !provider.is_active,
    });
    setUpdating(null);
    if (updated.status === "error") {
      push(updated.message, "error");
      return;
    }
    push(updated.data.is_active ? "Provider enabled" : "Provider disabled", "success");
    load();
  }

  return (
    <PageShell
      title="Payment Providers"
      breadcrumb={[{ label: "Operations" }, { label: "Providers" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        This catalog is sandbox metadata. Live Airtel Money, TNM Mpamba, and bank rails are not
        implemented. Only the simulated adapter can process payments.
      </p>

      {result === null && (
        <div className="grid gap-3 sm:grid-cols-2">
          <Skeleton className="h-28" />
          <Skeleton className="h-28" />
        </div>
      )}

      {result?.status === "error" && (
        <ErrorState
          kind={result.kind}
          description={result.message}
          requestId={result.requestId}
          onRetry={load}
        />
      )}

      {result?.status === "success" && result.data.length === 0 && (
        <EmptyState
          title="Provider catalog is empty"
          description="Seed sandbox rows with scripts/seed_providers.py in a non-production environment. The script is idempotent and stores no secrets."
        />
      )}

      {result?.status === "success" && result.data.length > 0 && (
        <div className="grid gap-3 sm:grid-cols-2">
          {result.data.map((provider) => (
            <Card key={provider.code}>
              <CardHeader className="flex items-center justify-between gap-2">
                <CardTitle>{provider.display_name}</CardTitle>
                <div className="flex flex-wrap items-center gap-1.5">
                  <Badge tone={provider.is_active ? "success" : "neutral"}>
                    {provider.is_active ? "Enabled" : "Disabled"}
                  </Badge>
                  <Badge tone="info">{provider.is_simulated ? "Simulated" : provider.environment}</Badge>
                </div>
              </CardHeader>
              <CardBody className="space-y-3 text-sm text-text-muted">
                <p className="font-mono text-xs text-text-subtle">
                  {provider.code} · {provider.environment} · priority {provider.priority}
                </p>
                <p>
                  Currencies {provider.supported_currencies.join(", ") || "—"} · Methods{" "}
                  {provider.supported_payment_methods.join(", ") || "—"}
                </p>
                <p>
                  Push {provider.capabilities.supports_push_payment ? "yes" : "no"} · Status{" "}
                  {provider.capabilities.supports_status_query ? "yes" : "no"} · Cancel{" "}
                  {provider.capabilities.supports_cancel ? "yes" : "no"} · Refund{" "}
                  {provider.capabilities.supports_refund ? "yes" : "no"} · Webhooks{" "}
                  {provider.capabilities.supports_webhooks ? "yes" : "no"} · QR{" "}
                  {provider.capabilities.supports_qr ? "yes" : "no"}
                </p>
                <p>
                  Adapter {provider.adapter_configured ? "configured (sandbox)" : "not configured"}
                </p>
                {canUpdate && (
                  <Button
                    variant="secondary"
                    size="sm"
                    loading={updating === provider.code}
                    disabled={!provider.adapter_configured && !provider.is_active}
                    onClick={() => void toggleActive(provider)}
                  >
                    {provider.is_active ? "Disable" : "Enable"}
                  </Button>
                )}
              </CardBody>
            </Card>
          ))}
        </div>
      )}
    </PageShell>
  );
}
