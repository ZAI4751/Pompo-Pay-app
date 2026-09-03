import type { LucideIcon } from "lucide-react";
import {
  Bell,
  CreditCard,
  KeySquare,
  Landmark,
  Lock,
  Plug,
  Scale,
  ScrollText,
  Server,
  ShieldCheck,
  SlidersHorizontal,
  Webhook,
} from "lucide-react";

export type SettingsCategoryId =
  | "general"
  | "security"
  | "users-roles"
  | "payments"
  | "providers"
  | "fees"
  | "notifications"
  | "webhooks"
  | "api"
  | "settlement"
  | "audit"
  | "system";

export type SettingsSupport = "live" | "partial" | "gap";

export interface SettingsCategory {
  id: SettingsCategoryId;
  href: `/settings/${SettingsCategoryId}`;
  label: string;
  shortLabel: string;
  description: string;
  icon: LucideIcon;
  support: SettingsSupport;
  /** UX-only; backend still authorizes each API. */
  permission?: string;
}

export const SETTINGS_CATEGORIES: SettingsCategory[] = [
  {
    id: "general",
    href: "/settings/general",
    label: "General",
    shortLabel: "General",
    description: "Platform identity, environment, and operator display preferences.",
    icon: SlidersHorizontal,
    support: "live",
  },
  {
    id: "security",
    href: "/settings/security",
    label: "Security",
    shortLabel: "Security",
    description: "Password, sessions, JWT lifetimes, rate limits, and CORS — as the process actually runs them.",
    icon: Lock,
    support: "partial",
  },
  {
    id: "users-roles",
    href: "/settings/users-roles",
    label: "Users & Roles",
    shortLabel: "Users",
    description: "RBAC roles and permissions. User directory listing is not exposed by the API.",
    icon: ShieldCheck,
    support: "partial",
    permission: "roles:read",
  },
  {
    id: "payments",
    href: "/settings/payments",
    label: "Payments",
    shortLabel: "Payments",
    description: "Payment lookup, QR, and payment-method administration already live on dedicated modules.",
    icon: CreditCard,
    support: "live",
    permission: "transactions:read",
  },
  {
    id: "providers",
    href: "/settings/providers",
    label: "Providers",
    shortLabel: "Providers",
    description: "Provider catalog, enablement, and rail configuration status from GET /providers.",
    icon: Plug,
    support: "live",
    permission: "providers:read",
  },
  {
    id: "fees",
    href: "/settings/fees",
    label: "Fees & Pricing",
    shortLabel: "Fees",
    description: "Fee totals from settlement records. Pricing schedule administration has no API.",
    icon: Scale,
    support: "partial",
    permission: "settlements:read",
  },
  {
    id: "notifications",
    href: "/settings/notifications",
    label: "Notifications",
    shortLabel: "Notify",
    description: "Signed-in operator inbox and per-user notification flags. No platform SMS/email gateway config.",
    icon: Bell,
    support: "partial",
  },
  {
    id: "webhooks",
    href: "/settings/webhooks",
    label: "Webhooks & Integrations",
    shortLabel: "Webhooks",
    description: "Inbound provider events and outbound delivery retries from process configuration.",
    icon: Webhook,
    support: "live",
    permission: "webhooks:read",
  },
  {
    id: "api",
    href: "/settings/api",
    label: "API / Developer",
    shortLabel: "API",
    description: "Integration clients, API keys, and machine scopes managed through /integrations.",
    icon: KeySquare,
    support: "live",
    permission: "api_keys:read",
  },
  {
    id: "settlement",
    href: "/settings/settlement",
    label: "Settlement & Reconciliation",
    shortLabel: "Settlement",
    description: "Live settlement and reconciliation summaries. No separate settlement-calendar API.",
    icon: Landmark,
    support: "live",
    permission: "settlements:read",
  },
  {
    id: "audit",
    href: "/settings/audit",
    label: "Audit / Compliance",
    shortLabel: "Audit",
    description: "Audit rows are written by services, but no list/query API exists yet.",
    icon: ScrollText,
    support: "gap",
  },
  {
    id: "system",
    href: "/settings/system",
    label: "System / Operational",
    shortLabel: "System",
    description: "Health, pools, logging, and other process settings. Changes require a new deployment.",
    icon: Server,
    support: "live",
  },
];

export const SETTINGS_CATEGORY_BY_ID = Object.fromEntries(
  SETTINGS_CATEGORIES.map((category) => [category.id, category]),
) as Record<SettingsCategoryId, SettingsCategory>;

export function isSettingsCategoryId(value: string): value is SettingsCategoryId {
  return value in SETTINGS_CATEGORY_BY_ID;
}

export const SETTINGS_MODULE_LINKS = {
  merchants: { href: "/merchants", label: "Merchants", permission: "merchants:read" },
  branches: { href: "/branches", label: "Branches", permission: "branches:read" },
  tills: { href: "/tills", label: "Tills", permission: "tills:read" },
  users: { href: "/users", label: "Users", permission: "users:read" },
  roles: { href: "/roles", label: "Roles", permission: "roles:read" },
  permissions: { href: "/permissions", label: "Permissions", permission: "permissions:read" },
  customers: { href: "/customers", label: "Customers", permission: "users:read" },
  payments: { href: "/payments", label: "Payments", permission: "transactions:read" },
  paymentMethods: { href: "/payment-methods", label: "Payment methods", permission: "users:read" },
  qr: { href: "/qr-codes", label: "QR codes", permission: "qr:read" },
  providers: { href: "/providers", label: "Providers", permission: "providers:read" },
  webhooks: { href: "/webhooks", label: "Webhooks", permission: "webhooks:read" },
  apiClients: { href: "/api-keys", label: "API clients", permission: "api_keys:read" },
  settlements: { href: "/settlements", label: "Settlements", permission: "settlements:read" },
  reconciliation: { href: "/reconciliation", label: "Reconciliation", permission: "reconciliation:read" },
  support: { href: "/support", label: "Support", permission: "users:read" },
  audit: { href: "/audit-logs", label: "Audit" },
  health: { href: "/system/health", label: "System health" },
  dashboard: { href: "/dashboard", label: "Dashboard" },
} as const;

export const BUSINESS_CONTEXT = {
  network: "Malawi",
  currency: "MWK",
  source: "Master Admin chrome — not a backend setting",
} as const;
