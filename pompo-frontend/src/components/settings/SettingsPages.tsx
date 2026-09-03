"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { SettingsShell } from "@/components/settings/SettingsShell";
import {
  BackendGapCard,
  ModuleLink,
  MonoValue,
  SettingRow,
  SettingsPanel,
  supportLabel,
  supportTone,
} from "@/components/settings/SettingPrimitives";
import { DisplayThemeForm } from "@/components/settings/PreferenceForms";
import { PasswordChangeForm, SessionRevokeForm } from "@/components/settings/SecurityForms";
import { NotificationPrefsForm } from "@/components/settings/PreferenceForms";
import { PlatformConfigPanel } from "@/components/settings/PlatformConfigPanel";
import { Badge } from "@/components/ui/Badge";
import { ErrorState } from "@/components/ui/ErrorState";
import { SkeletonCard } from "@/components/ui/SkeletonCard";
import { useAuth } from "@/lib/auth/AuthContext";
import { usePermissions } from "@/lib/auth/usePermissions";
import { healthService } from "@/lib/api/services/health";
import { providersService } from "@/lib/api/services/providers";
import { rolesService } from "@/lib/api/services/roles";
import { permissionsService } from "@/lib/api/services/permissions";
import { integrationsService } from "@/lib/api/services/integrations";
import { webhooksService } from "@/lib/api/services/webhooks";
import { settlementsService, reconciliationService } from "@/lib/api/services/settlements";
import { customersService, type NotificationInbox } from "@/lib/api/services/customers";
import {
  BUSINESS_CONTEXT,
  SETTINGS_CATEGORIES,
  SETTINGS_MODULE_LINKS,
} from "@/lib/settings/catalog";
import type { HealthResponse } from "@/lib/types/health";
import type { PaymentProvider } from "@/lib/types/payment";
import type { Role } from "@/lib/types/rbac";
import type { IntegrationClient } from "@/lib/types/integration";
import type { SettlementSummary, ReconciliationSummary } from "@/lib/types/settlement";
import type { ApiResult } from "@/lib/types/common";

export function SettingsOverviewPage() {
  const { hasPermission } = usePermissions();
  const visible = SETTINGS_CATEGORIES.filter(
    (category) => !category.permission || hasPermission(category.permission),
  );

  return (
    <SettingsShell title="Settings">
      <p className="max-w-3xl text-sm text-text-muted">
        Central configuration for the Master Admin control plane. Every control is bound to a
        live API or an explicit backend gap. Process settings are environment-backed and
        read-only. Dedicated operational modules are unchanged.
      </p>
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
        {visible.map((category) => {
          const Icon = category.icon;
          return (
            <Link
              key={category.id}
              href={category.href}
              className="rounded-2xl border border-border bg-white p-4 hover:border-primary dark:bg-slate-900"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-border text-text">
                  <Icon className="h-4 w-4" aria-hidden="true" />
                </div>
                <Badge tone={supportTone(category.support)}>{supportLabel(category.support)}</Badge>
              </div>
              <p className="mt-3 text-sm font-semibold text-text">{category.label}</p>
              <p className="mt-1 text-xs text-text-muted">{category.description}</p>
            </Link>
          );
        })}
      </div>
    </SettingsShell>
  );
}

export function GeneralSettingsPage() {
  const { user } = useAuth();

  return (
    <SettingsShell title="General" categoryId="general">
      <SettingsPanel
        title="Signed-in operator"
        description="GET /api/v1/auth/me. Profile fields are not editable — there is no user-update API."
      >
        <SettingRow label="Name" source="session" value={user?.full_name ?? "—"} />
        <SettingRow label="Email" source="session" value={<MonoValue>{user?.email ?? "—"}</MonoValue>} />
        <SettingRow label="Role" source="session" value={<MonoValue>{user?.role_code || user?.role_id}</MonoValue>} />
        <SettingRow
          label="Tenant scope"
          hint="Client-supplied tenant IDs are never trusted. Scope comes from the authenticated user."
          source="session"
          value={
            user?.merchant_id
              ? `Merchant ${user.merchant_id}${user.branch_id ? ` · Branch ${user.branch_id}` : ""}`
              : "Platform (no merchant binding)"
          }
        />
        <SettingRow label="Account status" source="session" value={user?.is_active ? "Active" : "Inactive"} />
      </SettingsPanel>

      <PlatformConfigPanel
        title="Platform identity"
        description="Name, version, and environment are process settings. They cannot be saved from this console."
        keys={["app_name", "app_version", "app_env", "api_v1_prefix"]}
      />

      <SettingsPanel
        title="Operating network"
        description="The Master Admin chrome currently presents Malawi / MWK. That label is not a writable backend setting."
      >
        <SettingRow label="Network" source="local" value={BUSINESS_CONTEXT.network} hint={BUSINESS_CONTEXT.source} />
        <SettingRow label="Currency" source="local" value={BUSINESS_CONTEXT.currency} />
      </SettingsPanel>

      <DisplayThemeForm />
    </SettingsShell>
  );
}

export function SecuritySettingsPage() {
  return (
    <SettingsShell title="Security" categoryId="security">
      <PasswordChangeForm />
      <SessionRevokeForm />
      <PlatformConfigPanel
        title="Token and abuse controls"
        description="JWT lifetimes, algorithm, CORS, hosts, and rate limits as loaded from the environment. Secrets are omitted by the API."
        keys={[
          "jwt_algorithm",
          "jwt_access_token_expire_minutes",
          "jwt_refresh_token_expire_days",
          "rate_limit_requests",
          "rate_limit_window_seconds",
          "rate_limit_auth_failures",
          "allowed_hosts",
          "cors_origins",
          "debug",
        ]}
      />
      <BackendGapCard
        title="No runtime security-policy API"
        contract="Missing: PATCH /api/v1/system/config, session inventory, MFA enrollment, IP allowlists"
        detail="Changing JWT secrets, TTLs, CORS, or rate limits requires a new deployment with updated environment variables. There is no MFA, IP allowlist, or per-device session list endpoint."
      />
    </SettingsShell>
  );
}

export function UsersRolesSettingsPage() {
  const { hasPermission } = usePermissions();
  const canRoles = hasPermission("roles:read");
  const canPermissions = hasPermission("permissions:read");
  const [roles, setRoles] = useState<ApiResult<Role[]> | null>(null);
  const [permissionCount, setPermissionCount] = useState<number | null>(null);

  useEffect(() => {
    if (canRoles) void rolesService.list().then(setRoles);
    if (canPermissions) {
      void permissionsService.list().then((result) => {
        setPermissionCount(result.status === "success" ? result.data.length : 0);
      });
    }
  }, [canRoles, canPermissions]);

  return (
    <SettingsShell title="Users & Roles" categoryId="users-roles">
      {!canRoles && (
        <ErrorState kind="forbidden" description="roles:read is required to inspect the role catalog." />
      )}
      {canRoles && roles === null && <SkeletonCard />}
      {canRoles && roles?.status === "error" && (
        <ErrorState kind={roles.kind} description={roles.message} requestId={roles.requestId} />
      )}
      {canRoles && roles?.status === "success" && (
        <SettingsPanel
          title="Role catalog"
          description="GET /api/v1/rbac/roles. Create, update, and grant permissions on the Roles module — this page does not duplicate those mutations."
          actions={
            <div className="flex flex-wrap gap-2">
              <ModuleLink href={SETTINGS_MODULE_LINKS.roles.href}>Open roles</ModuleLink>
              {canPermissions && (
                <ModuleLink href={SETTINGS_MODULE_LINKS.permissions.href}>Open permissions</ModuleLink>
              )}
            </div>
          }
        >
          <SettingRow
            label="Roles"
            source="api"
            value={`${roles.data.length} registered`}
          />
          <SettingRow
            label="System roles"
            source="api"
            value={`${roles.data.filter((role) => role.is_system_role).length} protected`}
          />
          <SettingRow
            label="Permission catalog"
            source="api"
            value={permissionCount === null ? "—" : `${permissionCount} codes`}
          />
          <div className="divide-y divide-border pt-2">
            {roles.data.map((role) => (
              <div key={role.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="font-medium text-text">{role.name}</p>
                  <p className="truncate font-mono text-xs text-text-subtle">{role.code}</p>
                </div>
                <div className="flex items-center gap-2">
                  <Badge tone={role.is_active ? "success" : "neutral"}>
                    {role.is_active ? "Active" : "Inactive"}
                  </Badge>
                  <span className="text-xs text-text-muted">{role.permission_codes.length} grants</span>
                </div>
              </div>
            ))}
          </div>
        </SettingsPanel>
      )}
      <BackendGapCard
        title="User directory is not an API"
        contract="Missing: GET /api/v1/users · POST /api/v1/users · PATCH /api/v1/users/{id}"
        detail="Role assignment exists at PUT /api/v1/rbac/users/{user_id}/role. Every user must retain one role. The Users screen documents this gap and does not invent a staff directory. Customer counts live on GET /customers/stats."
      />
    </SettingsShell>
  );
}

export function PaymentsSettingsPage() {
  const { hasPermission } = usePermissions();
  return (
    <SettingsShell title="Payments" categoryId="payments">
      <SettingsPanel
        title="Payment operations"
        description="Payment create, get, cancel, and process exist. Merchant-scoped GET /payments lists that merchant's payments. Platform administrators look up by reference. Attempts are nested on the payment record."
        actions={
          <div className="flex flex-wrap gap-2">
            {hasPermission("transactions:read") && (
              <ModuleLink href={SETTINGS_MODULE_LINKS.payments.href}>Look up payments</ModuleLink>
            )}
            {hasPermission("qr:read") && (
              <ModuleLink href={SETTINGS_MODULE_LINKS.qr.href}>QR codes</ModuleLink>
            )}
            {hasPermission("users:read") && (
              <ModuleLink href={SETTINGS_MODULE_LINKS.paymentMethods.href}>Payment methods</ModuleLink>
            )}
          </div>
        }
      >
        <SettingRow
          label="Lookup"
          source="api"
          value="GET /api/v1/payments/{reference}"
          hint="Platform administrators use reference lookup. Merchant-scoped operators see GET /payments."
        />
        <SettingRow
          label="List endpoint"
          source="api"
          value="GET /api/v1/payments (merchant-scoped)"
          hint="There is no global platform ledger. Payment attempts are nested on GET /payments/{reference}."
        />
        <SettingRow
          label="Currency"
          source="api"
          value="MWK on payment contracts"
          hint="Currency is a request field validated by the backend, not a Settings toggle."
        />
      </SettingsPanel>
    </SettingsShell>
  );
}

export function ProvidersSettingsPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("providers:read");
  const [result, setResult] = useState<ApiResult<PaymentProvider[]> | null>(null);

  useEffect(() => {
    if (canRead) void providersService.list().then(setResult);
  }, [canRead]);

  return (
    <SettingsShell title="Providers" categoryId="providers">
      {!canRead && (
        <ErrorState kind="forbidden" description="providers:read is required to view the catalog." />
      )}
      {canRead && result === null && <SkeletonCard />}
      {canRead && result?.status === "error" && (
        <ErrorState kind={result.kind} description={result.message} requestId={result.requestId} />
      )}
      {canRead && result?.status === "success" && (
        <SettingsPanel
          title="Provider catalog"
          description="GET /api/v1/providers. Enable, disable, and health inspection stay on the Providers module so this page cannot drift from that contract."
          actions={<ModuleLink href={SETTINGS_MODULE_LINKS.providers.href}>Manage providers</ModuleLink>}
        >
          <SettingRow label="Rails registered" source="api" value={`${result.data.length}`} />
          <SettingRow
            label="Active"
            source="api"
            value={`${result.data.filter((item) => item.is_active).length}`}
          />
          <div className="divide-y divide-border pt-2">
            {result.data.map((provider) => (
              <div key={provider.code} className="py-3 text-sm">
                <div className="flex items-center justify-between gap-3">
                  <p className="font-medium text-text">{provider.display_name}</p>
                  <Badge tone={provider.is_active ? "success" : "neutral"}>
                    {provider.is_active ? "Enabled" : "Disabled"}
                  </Badge>
                </div>
                <p className="mt-1 font-mono text-xs text-text-subtle">
                  {provider.code} · {provider.environment} · health {provider.health_state}
                </p>
                <p className="mt-1 text-xs text-text-muted">
                  Adapter {provider.adapter_configured ? "configured" : "not configured"} · contract{" "}
                  {provider.live_contract_ready ? "ready" : "not ready"} · timeout{" "}
                  {provider.configuration.timeout_seconds}s · auth{" "}
                  {provider.configuration.auth_configured ? "set" : "missing"}
                </p>
              </div>
            ))}
          </div>
        </SettingsPanel>
      )}
    </SettingsShell>
  );
}

export function FeesSettingsPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("settlements:read");
  const [summary, setSummary] = useState<ApiResult<SettlementSummary> | null>(null);

  useEffect(() => {
    if (canRead) void settlementsService.summary().then(setSummary);
  }, [canRead]);

  return (
    <SettingsShell title="Fees & Pricing" categoryId="fees">
      {!canRead && (
        <ErrorState kind="forbidden" description="settlements:read is required to view fee totals." />
      )}
      {canRead && summary === null && <SkeletonCard />}
      {canRead && summary?.status === "error" && (
        <ErrorState kind={summary.kind} description={summary.message} requestId={summary.requestId} />
      )}
      {canRead && summary?.status === "success" && (
        <SettingsPanel
          title="Observed fees"
          description="GET /api/v1/settlements/summary. These are recorded settlement totals, not an editable price list."
          actions={<ModuleLink href={SETTINGS_MODULE_LINKS.settlements.href}>Open settlements</ModuleLink>}
        >
          <SettingRow label="Settlements" source="api" value={String(summary.data.total_settlements)} />
          <SettingRow label="Gross" source="api" value={<MonoValue>{summary.data.total_gross}</MonoValue>} />
          <SettingRow
            label="Provider fees"
            source="api"
            value={<MonoValue>{summary.data.total_provider_fees}</MonoValue>}
          />
          <SettingRow
            label="POMPO fees"
            source="api"
            value={<MonoValue>{summary.data.total_pompo_fees}</MonoValue>}
          />
          <SettingRow
            label="Merchant net"
            source="api"
            value={<MonoValue>{summary.data.total_merchant_net}</MonoValue>}
          />
        </SettingsPanel>
      )}
      <BackendGapCard
        title="Pricing schedules have no admin API"
        contract="Model: pricing_schedules · Missing: GET/PATCH /api/v1/pricing"
        detail="Fee schedules exist in the database and are applied during settlement matching (merchant+provider > merchant > provider > platform default). There is no CRUD endpoint, so this console will not present an editable fee form."
      />
    </SettingsShell>
  );
}

export function NotificationsSettingsPage() {
  const [inbox, setInbox] = useState<ApiResult<NotificationInbox> | null>(null);

  useEffect(() => {
    void customersService.notifications().then(setInbox);
  }, []);

  return (
    <SettingsShell title="Notifications" categoryId="notifications">
      <SettingsPanel
        title="In-app inbox"
        description="GET /api/v1/notifications. This is the signed-in user's inbox, not a platform broadcast channel."
      >
        {inbox === null && <p className="text-sm text-text-muted">Loading inbox…</p>}
        {inbox?.status === "error" && (
          <ErrorState kind={inbox.kind} description={inbox.message} requestId={inbox.requestId} />
        )}
        {inbox?.status === "success" && (
          <>
            <SettingRow label="Unread" source="api" value={String(inbox.data.unread_count)} />
            <SettingRow label="Returned items" source="api" value={String(inbox.data.items.length)} />
          </>
        )}
      </SettingsPanel>
      <NotificationPrefsForm />
      <BackendGapCard
        title="No platform notification gateway"
        contract="Missing: SMTP/SMS/push provider configuration APIs"
        detail="CustomerPreference only stores per-user in-app flags. Phone verification is reported as not_configured. There is no operator UI for email templates, SMS senders, or push certificates because those backends do not exist."
      />
    </SettingsShell>
  );
}

export function WebhooksSettingsPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("webhooks:read");
  const [count, setCount] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canRead) return;
    void webhooksService.list({ limit: 50 }).then((result) => {
      if (result.status === "error") {
        setError(result.message);
        setCount(null);
        return;
      }
      setError(null);
      setCount(result.data.length);
    });
  }, [canRead]);

  return (
    <SettingsShell title="Webhooks & Integrations" categoryId="webhooks">
      {!canRead && (
        <ErrorState kind="forbidden" description="webhooks:read is required to inspect inbound events." />
      )}
      {canRead && (
        <SettingsPanel
          title="Inbound provider webhooks"
          description="GET /api/v1/webhooks. Events are ingested and audited by the backend. This page does not replay or forge callbacks."
          actions={<ModuleLink href={SETTINGS_MODULE_LINKS.webhooks.href}>Open webhook events</ModuleLink>}
        >
          {error && <p className="text-sm text-error">{error}</p>}
          {!error && (
            <SettingRow
              label="Recent events loaded"
              source="api"
              value={count === null ? "Loading…" : String(count)}
              hint="Capped at 50 on this summary. Use the Webhooks module to inspect payloads."
            />
          )}
        </SettingsPanel>
      )}
      <PlatformConfigPanel
        title="Outbound delivery policy"
        description="Retry bound and timeout come from process environment. They are not per-endpoint Settings fields."
        keys={["outbound_webhook_timeout_seconds", "outbound_webhook_max_attempts"]}
      />
      <SettingsPanel
        title="Outbound destinations"
        description="Merchant/POS outbound webhook URLs are stored on integration clients, not as a global Settings URL."
        actions={
          hasPermission("api_keys:read") ? (
            <ModuleLink href={SETTINGS_MODULE_LINKS.apiClients.href}>API clients</ModuleLink>
          ) : undefined
        }
      >
        <SettingRow
          label="Configuration surface"
          source="api"
          value="POST/PATCH /api/v1/integrations/clients and webhook endpoints"
        />
      </SettingsPanel>
    </SettingsShell>
  );
}

export function ApiSettingsPage() {
  const { hasPermission } = usePermissions();
  const canRead = hasPermission("api_keys:read");
  const [result, setResult] = useState<ApiResult<IntegrationClient[]> | null>(null);

  useEffect(() => {
    if (canRead) void integrationsService.list().then(setResult);
  }, [canRead]);

  return (
    <SettingsShell title="API / Developer" categoryId="api">
      {!canRead && (
        <ErrorState kind="forbidden" description="api_keys:read is required to list integration clients." />
      )}
      {canRead && result === null && <SkeletonCard />}
      {canRead && result?.status === "error" && (
        <ErrorState kind={result.kind} description={result.message} requestId={result.requestId} />
      )}
      {canRead && result?.status === "success" && (
        <SettingsPanel
          title="Integration clients"
          description="GET /api/v1/integrations/clients. Create, rotate, and revoke secrets on the API clients module — raw keys are shown only at creation."
          actions={<ModuleLink href={SETTINGS_MODULE_LINKS.apiClients.href}>Manage clients</ModuleLink>}
        >
          <SettingRow label="Clients" source="api" value={String(result.data.length)} />
          <SettingRow
            label="Not active"
            source="api"
            value={String(result.data.filter((item) => item.status !== "active").length)}
          />
          <div className="divide-y divide-border pt-2">
            {result.data.slice(0, 12).map((client) => (
              <div key={client.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                <div className="min-w-0">
                  <p className="truncate font-medium text-text">{client.name}</p>
                  <p className="truncate font-mono text-xs text-text-subtle">
                    {client.client_type} · {client.environment} · {client.keys[0]?.key_prefix ?? "no key"}
                  </p>
                </div>
                <Badge tone={client.status === "active" ? "success" : "neutral"}>{client.status}</Badge>
              </div>
            ))}
          </div>
        </SettingsPanel>
      )}
      <PlatformConfigPanel
        title="Public API prefix"
        description="The versioned HTTP prefix is an environment setting."
        keys={["api_v1_prefix", "cors_origins"]}
      />
    </SettingsShell>
  );
}

export function SettlementSettingsPage() {
  const { hasPermission } = usePermissions();
  const canSettle = hasPermission("settlements:read");
  const canRecon = hasPermission("reconciliation:read");
  const [settlement, setSettlement] = useState<ApiResult<SettlementSummary> | null>(null);
  const [recon, setRecon] = useState<ApiResult<ReconciliationSummary> | null>(null);

  useEffect(() => {
    if (canSettle) void settlementsService.summary().then(setSettlement);
    if (canRecon) void reconciliationService.summary().then(setRecon);
  }, [canSettle, canRecon]);

  return (
    <SettingsShell title="Settlement & Reconciliation" categoryId="settlement">
      {!canSettle && (
        <ErrorState kind="forbidden" description="settlements:read is required." />
      )}
      {canSettle && settlement === null && <SkeletonCard />}
      {canSettle && settlement?.status === "error" && (
        <ErrorState
          kind={settlement.kind}
          description={settlement.message}
          requestId={settlement.requestId}
        />
      )}
      {canSettle && settlement?.status === "success" && (
        <SettingsPanel
          title="Settlement totals"
          description="GET /api/v1/settlements/summary. Ingest remains HMAC-signed at POST /api/v1/settlements/ingest/{provider_code}."
          actions={<ModuleLink href={SETTINGS_MODULE_LINKS.settlements.href}>Open settlements</ModuleLink>}
        >
          <SettingRow label="Records" source="api" value={String(settlement.data.total_settlements)} />
          <SettingRow label="Gross" source="api" value={<MonoValue>{settlement.data.total_gross}</MonoValue>} />
          <SettingRow
            label="Merchant net"
            source="api"
            value={<MonoValue>{settlement.data.total_merchant_net}</MonoValue>}
          />
        </SettingsPanel>
      )}
      {canRecon && recon?.status === "success" && (
        <SettingsPanel
          title="Reconciliation"
          description="GET /api/v1/reconciliation/summary. Resolution notes are recorded on the Reconciliation module."
          actions={
            <ModuleLink href={SETTINGS_MODULE_LINKS.reconciliation.href}>Open reconciliation</ModuleLink>
          }
        >
          <SettingRow label="Matched" source="api" value={String(recon.data.matched)} />
          <SettingRow label="Unmatched" source="api" value={String(recon.data.unmatched)} />
          <SettingRow label="Discrepancy" source="api" value={String(recon.data.discrepancy)} />
          <SettingRow label="Matched rate" source="api" value={recon.data.matched_rate} />
        </SettingsPanel>
      )}
      <BackendGapCard
        title="No settlement calendar or cutoff API"
        contract="Missing: settlement window, payout calendar, or auto-recon schedule configuration"
        detail="Reconciliation runs can be created through the existing reconciliation API. There is no Settings endpoint for cut-off times, payout calendars, or scheduled job toggles."
      />
    </SettingsShell>
  );
}

export function AuditSettingsPage() {
  return (
    <SettingsShell title="Audit / Compliance" categoryId="audit">
      <BackendGapCard
        title="Audit log table has no query API"
        contract="Model: audit_logs · Missing: GET /api/v1/audit-logs"
        detail="Services write immutable audit rows for payments, webhooks, settlements, instruments, and other mutations. Rows have no updated_at and cannot be soft-deleted. Until a list endpoint exists, this console will not invent an audit viewer or fake events."
      />
      <SettingsPanel
        title="What is already audited"
        description="Writes go through service-layer helpers. Authorization remains server-side."
        actions={<ModuleLink href={SETTINGS_MODULE_LINKS.audit.href}>Open Audit</ModuleLink>}
      >
        <SettingRow label="Storage" value="PostgreSQL table audit_logs" />
        <SettingRow label="Mutability" value="Append-only (no updated_at, no soft delete)" />
        <SettingRow
          label="Existing UI"
          value="Operations → Audit states the gap. It does not present mock logs."
        />
      </SettingsPanel>
    </SettingsShell>
  );
}

export function SystemSettingsPage() {
  const [health, setHealth] = useState<ApiResult<HealthResponse> | null>(null);

  useEffect(() => {
    void healthService.check().then(setHealth);
  }, []);

  return (
    <SettingsShell title="System / Operational" categoryId="system">
      <SettingsPanel
        title="Runtime health"
        description="GET /api/v1/health. Liveness does not depend on dependencies; readiness does."
        actions={<ModuleLink href={SETTINGS_MODULE_LINKS.health.href}>Open health</ModuleLink>}
      >
        {health === null && <p className="text-sm text-text-muted">Checking health…</p>}
        {health?.status === "error" && (
          <ErrorState kind={health.kind} description={health.message} requestId={health.requestId} />
        )}
        {health?.status === "success" && (
          <>
            <SettingRow label="Status" source="api" value={health.data.status} />
            <SettingRow label="Environment" source="api" value={health.data.environment} />
            <SettingRow label="Version" source="api" value={<MonoValue>{health.data.version}</MonoValue>} />
            <SettingRow
              label="Check duration"
              source="api"
              value={`${health.data.response_time_ms} ms`}
            />
            {Object.entries(health.data.components).map(([name, component]) => (
              <SettingRow
                key={name}
                label={name}
                source="api"
                value={`${component.status}${component.healthy ? "" : " · unhealthy"}`}
              />
            ))}
          </>
        )}
      </SettingsPanel>
      <PlatformConfigPanel
        title="Process resources and logging"
        description="Connection pools and log format are environment settings. Changing them requires a new process."
        keys={[
          "database_pool_size",
          "database_max_overflow",
          "database_pool_timeout",
          "database_echo",
          "redis_max_connections",
          "log_level",
          "log_json",
          "writable",
          "configuration_source",
        ]}
      />
      <BackendGapCard
        title="No live config mutation or worker-toggle API"
        contract="Missing: PATCH /system/config · Celery queue admin · Redis flush"
        detail="Celery broker URLs and Redis DSNs are secrets and are excluded from GET /system/config. Services and Monitoring nav items remain reserved until those APIs exist."
      />
    </SettingsShell>
  );
}
