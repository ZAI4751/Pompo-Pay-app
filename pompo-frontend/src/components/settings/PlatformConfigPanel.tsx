"use client";

import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { MonoValue, SettingRow, SettingsPanel } from "@/components/settings/SettingPrimitives";
import { usePlatformConfig } from "@/lib/settings/usePlatformConfig";
import type { PlatformConfig } from "@/lib/types/system";

type ConfigKey = keyof PlatformConfig;

export function PlatformConfigPanel({
  title,
  description,
  keys,
}: {
  title: string;
  description: string;
  keys: ConfigKey[];
}) {
  const { result, load, config } = usePlatformConfig();

  if (result === null) return <SkeletonCard />;
  if (result.status === "error") {
    return (
      <ErrorState
        kind={result.kind}
        description={result.message}
        requestId={result.requestId}
        onRetry={load}
      />
    );
  }

  return (
    <SettingsPanel
      title={title}
      description={description}
        badge={
          <span className="text-[11px] uppercase tracking-[0.12em] text-text-subtle">
            GET /api/v1/system/config · platform_admin · not writable
          </span>
        }
    >
      {keys.map((key) => (
        <SettingRow
          key={key}
          label={labelFor(key)}
          hint={hintFor(key)}
          source="environment"
          value={<MonoValue>{formatValue(config?.[key])}</MonoValue>}
        />
      ))}
    </SettingsPanel>
  );
}

function labelFor(key: ConfigKey): string {
  const labels: Partial<Record<ConfigKey, string>> = {
    app_name: "Application name",
    app_version: "Version",
    app_env: "Environment",
    debug: "Debug mode",
    api_v1_prefix: "API prefix",
    allowed_hosts: "Allowed hosts",
    cors_origins: "CORS origins",
    database_pool_size: "Database pool size",
    database_max_overflow: "Database max overflow",
    database_pool_timeout: "Database pool timeout (s)",
    database_echo: "SQL echo",
    redis_max_connections: "Redis max connections",
    jwt_algorithm: "JWT algorithm",
    jwt_access_token_expire_minutes: "Access token lifetime (minutes)",
    jwt_refresh_token_expire_days: "Refresh token lifetime (days)",
    rate_limit_requests: "General rate limit (requests)",
    rate_limit_window_seconds: "Rate-limit window (seconds)",
    rate_limit_auth_failures: "Auth failure rate limit",
    outbound_webhook_timeout_seconds: "Outbound webhook timeout (s)",
    outbound_webhook_max_attempts: "Outbound webhook max attempts",
    log_level: "Log level",
    log_json: "JSON logs",
    configuration_source: "Configuration source",
    writable: "API writable",
  };
  return labels[key] ?? key;
}

function hintFor(key: ConfigKey): string | undefined {
  const hints: Partial<Record<ConfigKey, string>> = {
    debug: "Forced false in production settings. Not editable from this console.",
    cors_origins: "Browser origins permitted to call the API.",
    jwt_algorithm: "Signing secret is never returned.",
    writable: "Deploy with new environment variables to change process settings.",
    outbound_webhook_max_attempts: "Celery outbound delivery bound. Inbound provider webhooks are a separate module.",
  };
  return hints[key];
}

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (Array.isArray(value)) return value.length ? value.join(", ") : "—";
  return String(value);
}
