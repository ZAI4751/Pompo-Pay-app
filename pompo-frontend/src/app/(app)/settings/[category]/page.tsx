"use client";

import { useParams } from "next/navigation";
import { ErrorState } from "@/components/ui/ErrorState";
import { SettingsShell } from "@/components/settings/SettingsShell";
import {
  ApiSettingsPage,
  AuditSettingsPage,
  FeesSettingsPage,
  GeneralSettingsPage,
  NotificationsSettingsPage,
  PaymentsSettingsPage,
  ProvidersSettingsPage,
  SecuritySettingsPage,
  SettlementSettingsPage,
  SystemSettingsPage,
  UsersRolesSettingsPage,
  WebhooksSettingsPage,
} from "@/components/settings/SettingsPages";
import { isSettingsCategoryId, SETTINGS_CATEGORY_BY_ID } from "@/lib/settings/catalog";
import { usePermissions } from "@/lib/auth/usePermissions";

export default function Page() {
  const params = useParams<{ category: string | string[] }>();
  const raw = params.category;
  const category = Array.isArray(raw) ? raw[0] : raw;
  const { hasPermission } = usePermissions();

  if (!category || !isSettingsCategoryId(category)) {
    return (
      <SettingsShell title="Settings">
        <ErrorState kind="not_found" description="That settings category does not exist." />
      </SettingsShell>
    );
  }

  const meta = SETTINGS_CATEGORY_BY_ID[category];
  if (meta.permission && !hasPermission(meta.permission)) {
    return (
      <SettingsShell title={meta.label} categoryId={category}>
        <ErrorState
          kind="forbidden"
          description={`You do not have ${meta.permission}, so this settings category is hidden.`}
        />
      </SettingsShell>
    );
  }

  switch (category) {
    case "general":
      return <GeneralSettingsPage />;
    case "security":
      return <SecuritySettingsPage />;
    case "users-roles":
      return <UsersRolesSettingsPage />;
    case "payments":
      return <PaymentsSettingsPage />;
    case "providers":
      return <ProvidersSettingsPage />;
    case "fees":
      return <FeesSettingsPage />;
    case "notifications":
      return <NotificationsSettingsPage />;
    case "webhooks":
      return <WebhooksSettingsPage />;
    case "api":
      return <ApiSettingsPage />;
    case "settlement":
      return <SettlementSettingsPage />;
    case "audit":
      return <AuditSettingsPage />;
    case "system":
      return <SystemSettingsPage />;
    default:
      return (
        <SettingsShell title="Settings">
          <ErrorState kind="not_found" description="That settings category does not exist." />
        </SettingsShell>
      );
  }
}
