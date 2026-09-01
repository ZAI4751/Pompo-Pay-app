"use client";

import { useEffect, useState } from "react";
import { PageShell } from "@/components/layout/PageShell";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { ErrorState } from "@/components/ui/ErrorState";
import { HealthBadge } from "@/components/ui/StatusBadge";
import { MockDataBadge } from "@/components/ui/MockDataBadge";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { healthService } from "@/lib/api/services/health";
import { useAuth } from "@/lib/auth/AuthContext";
import type { HealthResponse } from "@/lib/types/health";
import type { ApiResult } from "@/lib/types/common";

function toBadge(healthy: boolean, status: string): "healthy" | "degraded" | "down" | "unknown" {
  if (healthy) return "healthy";
  if (status === "degraded") return "degraded";
  if (status === "unknown") return "unknown";
  return "down";
}

export default function HealthPage() {
  const { isDemoSession } = useAuth();
  const [result, setResult] = useState<ApiResult<HealthResponse> | null>(null);

  const load = () => {
    void healthService.check().then(setResult);
  };

  useEffect(() => {
    void healthService.check().then(setResult);
  }, []);

  return (
    <PageShell
      title="Health"
      breadcrumb={[{ label: "System" }, { label: "Health" }]}
      actions={isDemoSession ? <MockDataBadge /> : undefined}
    >
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

      {result?.status === "success" && (
        <div className="space-y-4">
          <Card>
            <CardHeader className="flex items-center justify-between">
              <div>
                <CardTitle>GET /api/v1/health</CardTitle>
                <p className="text-xs text-text-muted">
                  {result.data.environment} · {result.data.version} · {result.data.response_time_ms} ms
                </p>
              </div>
              <HealthBadge
                state={toBadge(result.data.status === "healthy", result.data.status)}
              />
            </CardHeader>
            <CardBody className="space-y-2">
              {Object.entries(result.data.components).map(([name, component]) => (
                <div
                  key={name}
                  className="flex items-center justify-between rounded-sm border border-border px-3 py-2.5"
                >
                  <div>
                    <p className="text-sm font-medium capitalize text-text">{name}</p>
                    {component.details && (
                      <p className="text-[11px] text-text-subtle">{JSON.stringify(component.details)}</p>
                    )}
                  </div>
                  <HealthBadge state={toBadge(component.healthy, component.status)} />
                </div>
              ))}
            </CardBody>
          </Card>
        </div>
      )}
    </PageShell>
  );
}
