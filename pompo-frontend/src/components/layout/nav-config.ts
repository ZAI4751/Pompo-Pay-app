import type { LucideIcon } from "lucide-react";
import {
  QrCode,
  LayoutDashboard,
  CreditCard,
  Plug,
  Webhook,
  Store,
  GitBranch,
  MonitorSmartphone,
  Users,
  ContactRound,
  ShieldCheck,
  KeyRound,
  KeySquare,
  Settings,
  HeartPulse,
  Landmark,
  Scale,
  LifeBuoy,
  ScrollText,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Permission code required to see this item; omitted = visible to all authenticated users. */
  permission?: string;
  /** True if the backing backend endpoint doesn't exist yet. */
  comingSoon?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    label: "Overview",
    items: [{ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Organization",
    items: [
      { label: "Merchants", href: "/merchants", icon: Store, permission: "merchants:read" },
      { label: "Branches", href: "/branches", icon: GitBranch, permission: "branches:read" },
      { label: "Tills", href: "/tills", icon: MonitorSmartphone, permission: "tills:read" },
      { label: "Customers", href: "/customers", icon: ContactRound, permission: "users:read" },
      { label: "Users", href: "/users", icon: Users, permission: "users:read" },
      { label: "Roles", href: "/roles", icon: ShieldCheck, permission: "roles:read" },
      { label: "Permissions", href: "/permissions", icon: KeyRound, permission: "permissions:read" },
    ],
  },
  {
    label: "Payments",
    items: [
      { label: "Payments", href: "/payments", icon: CreditCard, permission: "transactions:read" },
      { label: "Payment methods", href: "/payment-methods", icon: CreditCard, permission: "users:read" },
      { label: "QR Codes", href: "/qr-codes", icon: QrCode, permission: "qr:read" },
      { label: "Providers", href: "/providers", icon: Plug, permission: "providers:read" },
    ],
  },
  {
    label: "Integrations",
    items: [
      { label: "API Keys", href: "/api-keys", icon: KeySquare, permission: "api_keys:read" },
      { label: "Webhooks", href: "/webhooks", icon: Webhook, permission: "webhooks:read" },
    ],
  },
  {
    label: "Financial operations",
    items: [
      { label: "Settlements", href: "/settlements", icon: Landmark, permission: "settlements:read" },
      { label: "Reconciliation", href: "/reconciliation", icon: Scale, permission: "reconciliation:read" },
    ],
  },
  {
    label: "Operations",
    items: [
      { label: "Support", href: "/support", icon: LifeBuoy, permission: "users:read" },
      { label: "Audit", href: "/audit-logs", icon: ScrollText },
    ],
  },
  {
    label: "Configuration",
    items: [
      { label: "Settings", href: "/settings", icon: Settings },
      { label: "Health", href: "/system/health", icon: HeartPulse },
    ],
  },
];
