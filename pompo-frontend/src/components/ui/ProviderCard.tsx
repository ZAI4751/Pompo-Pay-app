"use client";

import { Badge } from "./Badge";
import { Button } from "./Button";
import { Card, CardBody, CardHeader, CardTitle } from "./Card";
import { HealthIndicator } from "./HealthIndicator";
import { cn } from "@/lib/utils/cn";
import type { PaymentProvider } from "@/lib/types/payment";

function healthTone(state: string): "success" | "warning" | "error" | "neutral" | "info" {
  if (state === "active") return "success";
  if (state === "degraded") return "warning";
  if (state === "unavailable") return "error";
  return "neutral";
}

function liveState(provider: PaymentProvider): "active" | "degraded" | "unavailable" | "idle" {
  if (!provider.is_active) return "idle";
  if (provider.health_state === "degraded") return "degraded";
  if (provider.health_state === "unavailable") return "unavailable";
  if (provider.health_state === "active") return "active";
  return "idle";
}

interface ProviderCardProps {
  provider: PaymentProvider;
  canUpdate?: boolean;
  updating?: boolean;
  compact?: boolean;
  onToggle?: (provider: PaymentProvider) => void;
  onHealth?: (code: string) => void;
}

export function ProviderCard({
  provider,
  canUpdate,
  updating,
  compact,
  onToggle,
  onHealth,
}: ProviderCardProps) {
  return (
    <Card interactive className="h-full">
      <CardHeader className="flex items-start justify-between gap-4">
        <div className="min-w-0">
          <CardTitle>{provider.display_name}</CardTitle>
          <p className="mt-1 truncate font-mono text-[11px] text-text-subtle">
            {provider.code} · {provider.provider_type} · priority {provider.priority}
          </p>
        </div>
        <div className="flex max-w-[12rem] flex-wrap items-center justify-end gap-1.5">
          <Badge tone={provider.is_active ? "success" : "neutral"}>
            {provider.is_active ? "Enabled" : "Disabled"}
          </Badge>
          <Badge tone={healthTone(provider.health_state)}>{provider.health_state}</Badge>
          <Badge tone="info">{provider.is_simulated ? "Simulated" : provider.environment}</Badge>
        </div>
      </CardHeader>
      <CardBody className="space-y-3 text-sm text-text-muted">
        <HealthIndicator
          state={liveState(provider)}
          label={
            provider.live_contract_ready
              ? "Contract ready"
              : "Awaiting contract"
          }
        />
        {!compact && (
          <>
            <p>
              Currencies {provider.supported_currencies.join(", ") || "—"} · Methods{" "}
              {provider.supported_payment_methods.join(", ") || "—"}
            </p>
            <p>
              Push {provider.capabilities.supports_push_payment ? "yes" : "no"} · Status{" "}
              {provider.capabilities.supports_status_query ? "yes" : "no"} · Cancel{" "}
              {provider.capabilities.supports_cancel ? "yes" : "no"} · Refund{" "}
              {provider.capabilities.supports_refund ? "yes" : "no"}
            </p>
            <p>
              Adapter {provider.adapter_configured ? "registered" : "missing"} · Configuration{" "}
              {provider.configuration.configuration_complete ? "complete" : "incomplete"} · Rail{" "}
              {provider.configuration.rail_environment}
            </p>
            <p>
              Auth {provider.configuration.auth_configured ? "Configured" : "Not configured"} ·
              Signing {provider.configuration.signing_configured ? "Configured" : "Not configured"} ·
              Base URL {provider.configuration.base_url_configured ? "Configured" : "Not configured"}
            </p>
            {provider.health.message && (
              <p className={cn("text-xs")}>{provider.health.message}</p>
            )}
          </>
        )}
        {canUpdate && (
          <div className="flex flex-wrap gap-2">
            <Button
              variant="secondary"
              size="sm"
              loading={updating}
              disabled={!provider.live_contract_ready && !provider.is_active}
              onClick={() => onToggle?.(provider)}
            >
              {provider.is_active ? "Disable" : "Enable"}
            </Button>
            <Button variant="secondary" size="sm" loading={updating} onClick={() => onHealth?.(provider.code)}>
              Check health
            </Button>
          </div>
        )}
      </CardBody>
    </Card>
  );
}
