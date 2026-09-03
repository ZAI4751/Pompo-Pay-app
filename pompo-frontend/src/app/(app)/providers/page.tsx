"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { ErrorState } from "@/components/ui/ErrorState";
import { EmptyState } from "@/components/ui/EmptyState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { ProviderCard } from "@/components/ui/ProviderCard";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { Stagger, StaggerItem } from "@/components/motion/Stagger";
import { providersService } from "@/lib/api/services/providers";
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
    void providersService.list().then(setResult);
  };

  useEffect(() => {
    void providersService.list().then(setResult);
  }, []);

  async function toggleActive(provider: PaymentProvider) {
    setUpdating(provider.code);
    const updated = provider.is_active
      ? await providersService.disable(provider.code)
      : await providersService.enable(provider.code);
    setUpdating(null);
    if (updated.status === "error") {
      push(updated.message, "error");
      return;
    }
    push(updated.data.is_active ? "Provider enabled" : "Provider disabled", "success");
    load();
  }

  async function refreshHealth(code: string) {
    setUpdating(code);
    const inspected = await providersService.inspectHealth(code);
    setUpdating(null);
    if (inspected.status === "error") {
      push(inspected.message, "error");
      return;
    }
    load();
  }

  return (
    <PageShell
      title="Payment Providers"
      breadcrumb={[{ label: "Payments" }, { label: "Providers" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
      <p className="mb-4 max-w-2xl text-sm text-text-muted">
        Rails are never treated as live merely because they appear in the catalog.
        Simulated sandbox is labeled SIMULATED. TNM Mpamba and Standard Bank stay
        CONTRACT NOT READY until a live contract exists. Credentials are never shown.
      </p>

      {result === null && (
        <div className="grid gap-3 sm:grid-cols-2">
          <SkeletonCard />
          <SkeletonCard />
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
        <Stagger className="grid gap-4 sm:grid-cols-2">
          {result.data.map((provider) => (
            <StaggerItem key={provider.code}>
              <ProviderCard
                provider={provider}
                canUpdate={canUpdate}
                updating={updating === provider.code}
                onToggle={(item) => void toggleActive(item)}
                onHealth={(code) => void refreshHealth(code)}
              />
            </StaggerItem>
          ))}
        </Stagger>
      )}
    </PageShell>
  );
}
