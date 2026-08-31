import type { LucideIcon } from "lucide-react";
import {
  LayoutDashboard,
  ArrowLeftRight,
  CreditCard,
  Plug,
  Webhook,
  AlertOctagon,
  Store,
  GitBranch,
  MonitorSmartphone,
  Users,
  ShieldCheck,
  KeyRound,
  KeySquare,
  ScrollText,
  Lock,
  Settings,
  FileBarChart,
  BarChart3,
  Download,
  HeartPulse,
  Server,
  Activity,
} from "lucide-react";

export interface NavItem {
  label: string;
  href: string;
  icon: LucideIcon;
  /** Permission code required to see this item; omitted = visible to all authenticated users. */
  permission?: string;
  /** True if the backing backend endpoint doesn't exist yet -- routes to a ComingSoon screen. */
  comingSoon?: boolean;
}

export interface NavGroup {
  label: string;
  items: NavItem[];
}

export const navGroups: NavGroup[] = [
  {
    label: "",
    items: [{ label: "Dashboard", href: "/dashboard", icon: LayoutDashboard }],
  },
  {
    label: "Operations",
    items: [
      { label: "Transactions", href: "/transactions", icon: ArrowLeftRight, comingSoon: true },
      { label: "Payments", href: "/payments", icon: CreditCard, comingSoon: true },
      { label: "Payment Providers", href: "/providers", icon: Plug, comingSoon: true },
      { label: "Webhooks", href: "/webhooks", icon: Webhook, comingSoon: true },
      { label: "Failed / Exceptions", href: "/exceptions", icon: AlertOctagon, comingSoon: true },
    ],
  },
  {
    label: "Merchants",
    items: [
      { label: "Merchants", href: "/merchants", icon: Store, permission: "merchants:read" },
      { label: "Branches", href: "/branches", icon: GitBranch, comingSoon: true },
      { label: "Tills", href: "/tills", icon: MonitorSmartphone, comingSoon: true },
    ],
  },
  {
    label: "Identity & Access",
    items: [
      { label: "Users", href: "/users", icon: Users, permission: "users:read" },
      { label: "Roles", href: "/roles", icon: ShieldCheck, permission: "roles:read" },
      { label: "Permissions", href: "/permissions", icon: KeyRound, permission: "roles:read" },
    ],
  },
  {
    label: "Platform",
    items: [
      { label: "API Keys", href: "/api-keys", icon: KeySquare, comingSoon: true },
      { label: "Audit Logs", href: "/audit-logs", icon: ScrollText, permission: "audit_logs:read" },
      { label: "Security", href: "/security", icon: Lock, comingSoon: true },
      { label: "System Settings", href: "/settings", icon: Settings, comingSoon: true },
    ],
  },
  {
    label: "Reporting",
    items: [
      { label: "Reports", href: "/reports", icon: FileBarChart, comingSoon: true },
      { label: "Analytics", href: "/analytics", icon: BarChart3, comingSoon: true },
      { label: "Exports", href: "/exports", icon: Download, comingSoon: true },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Health", href: "/system/health", icon: HeartPulse, comingSoon: true },
      { label: "Services", href: "/system/services", icon: Server, comingSoon: true },
      { label: "Monitoring", href: "/system/monitoring", icon: Activity, comingSoon: true },
    ],
  },
];
