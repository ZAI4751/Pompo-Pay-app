/**
 * Typed mock/demo data. Nothing here is presented as real backend data --
 * every screen that reads from this file also renders a visible "Demo
 * data" indicator (see components/ui/MockDataBadge.tsx).
 */

import type { AuthenticatedUser } from "@/lib/types/auth";
import type { Permission, Role, RoleDetail } from "@/lib/types/rbac";
import type { Merchant, Branch, Till } from "@/lib/types/merchant";
import type { StaffUser } from "@/lib/types/staff-user";
import type { Transaction } from "@/lib/types/transaction";

export const mockPermissions: Permission[] = [
  { id: "p1", code: "users:read", description: "View staff user accounts" },
  { id: "p2", code: "users:update", description: "Edit staff user accounts" },
  { id: "p3", code: "roles:read", description: "View roles and their permissions" },
  { id: "p4", code: "roles:update", description: "Modify role permission grants" },
  { id: "p5", code: "merchants:read", description: "View merchants" },
  { id: "p6", code: "merchants:update", description: "Edit merchant details" },
  { id: "p7", code: "transactions:read", description: "View transactions" },
  { id: "p8", code: "transactions:refund", description: "Issue transaction refunds" },
  { id: "p9", code: "api_keys:read", description: "View API keys" },
  { id: "p10", code: "audit_logs:read", description: "View audit logs" },
];

export const mockRoles: Role[] = [
  {
    id: "r1",
    code: "platform_admin",
    name: "Platform Admin",
    description: "Full system access across all merchants.",
    is_system_role: true,
    is_active: true,
    permission_codes: mockPermissions.map((permission) => permission.code),
  },
  {
    id: "r2",
    code: "merchant_owner",
    name: "Merchant Owner",
    description: "Full access within a single merchant.",
    is_system_role: true,
    is_active: true,
    permission_codes: mockPermissions.slice(0, 7).map((permission) => permission.code),
  },
  {
    id: "r3",
    code: "branch_manager",
    name: "Branch Manager",
    description: "Manages a branch's tills and staff.",
    is_system_role: true,
    is_active: true,
    permission_codes: mockPermissions.slice(0, 4).map((permission) => permission.code),
  },
  {
    id: "r4",
    code: "cashier",
    name: "Cashier",
    description: "Processes transactions at a till.",
    is_system_role: true,
    is_active: true,
    permission_codes: mockPermissions.slice(0, 2).map((permission) => permission.code),
  },
  {
    id: "r5",
    code: "regional_auditor",
    name: "Regional Auditor",
    description: "Custom role: read-only access for compliance reviews.",
    is_system_role: false,
    is_active: true,
    permission_codes: mockPermissions.slice(0, 3).map((permission) => permission.code),
  },
];

export const mockRoleDetails: Record<string, RoleDetail> = Object.fromEntries(
  mockRoles.map((role) => [
    role.id,
    {
      ...role,
      permissions: mockPermissions.filter((permission) => role.permission_codes.includes(permission.code)),
    },
  ]),
);

export const mockMerchants: Merchant[] = [
  {
    id: "m1",
    name: "Chikondi General Store",
    legal_name: "Chikondi Enterprises Ltd",
    registration_number: "C123",
    contact_email: "owner@chikondi.mw",
    contact_phone: "+265 991 000 001",
    is_active: true,
  },
  {
    id: "m2",
    name: "Mzuzu Fresh Market",
    legal_name: "Mzuzu Fresh Market Ltd",
    registration_number: null,
    contact_email: "admin@mzuzufresh.mw",
    contact_phone: "+265 991 222 333",
    is_active: true,
  },
  {
    id: "m3",
    name: "Lilongwe Pharmacy Group",
    legal_name: "LPG Holdings",
    registration_number: null,
    contact_email: "finance@lpg.mw",
    contact_phone: "+265 888 444 555",
    is_active: false,
  },
];

export const mockBranches: Branch[] = [
  {
    id: "b1",
    merchant_id: "m1",
    name: "Area 47 Branch",
    address: "Area 47, Lilongwe",
    is_active: true,
  },
  {
    id: "b2",
    merchant_id: "m1",
    name: "Old Town Branch",
    address: "Old Town, Lilongwe",
    is_active: true,
  },
  {
    id: "b3",
    merchant_id: "m2",
    name: "Mzuzu Central",
    address: "Mzuzu City Centre",
    is_active: true,
  },
];

export const mockTills: Till[] = [
  {
    id: "t1",
    branch_id: "b1",
    merchant_id: "m1",
    code: "POS-1",
    name: "Front Counter",
    is_active: true,
  },
  {
    id: "t2",
    branch_id: "b1",
    merchant_id: "m1",
    code: "POS-2",
    name: "Till 2",
    is_active: true,
  },
];

export const mockUsers: StaffUser[] = [
  {
    id: "u1",
    email: "grace.banda@chikondi.mw",
    full_name: "Grace Banda",
    role_id: "r4",
    role_name: "Cashier",
    merchant_id: "m1",
    merchant_name: "Chikondi General Store",
    branch_id: "b1",
    branch_name: "Area 47 Branch",
    is_active: true,
    last_login_at: "2026-08-29T14:22:00Z",
    created_at: "2026-05-13T09:00:00Z",
  },
  {
    id: "u2",
    email: "owner@chikondi.mw",
    full_name: "Chikondi Phiri",
    role_id: "r2",
    role_name: "Merchant Owner",
    merchant_id: "m1",
    merchant_name: "Chikondi General Store",
    branch_id: null,
    branch_name: null,
    is_active: true,
    last_login_at: "2026-08-30T07:10:00Z",
    created_at: "2026-05-12T08:05:00Z",
  },
  {
    id: "u3",
    email: "platform.admin@pompo.mw",
    full_name: "Zai Admin",
    role_id: "r1",
    role_name: "Platform Admin",
    merchant_id: null,
    merchant_name: null,
    branch_id: null,
    branch_name: null,
    is_active: true,
    last_login_at: "2026-08-30T08:00:00Z",
    created_at: "2026-01-01T00:00:00Z",
  },
  {
    id: "u4",
    email: "suspended.cashier@lpg.mw",
    full_name: "Former Employee",
    role_id: "r4",
    role_name: "Cashier",
    merchant_id: "m3",
    merchant_name: "Lilongwe Pharmacy Group",
    branch_id: "b5",
    branch_name: "Kanengo Branch",
    is_active: false,
    last_login_at: "2026-07-02T10:00:00Z",
    created_at: "2026-04-21T08:00:00Z",
  },
];

export const mockTransactions: Transaction[] = [
  {
    id: "t1",
    reference: "TXN-9F2A1C4B",
    merchant_id: "m1",
    merchant_name: "Chikondi General Store",
    branch_name: "Area 47 Branch",
    till_name: "Front Counter",
    amount: "2500.00",
    currency: "MWK",
    status: "success",
    provider_name: "Airtel Money",
    created_at: "2026-08-30T07:12:00Z",
    completed_at: "2026-08-30T07:12:04Z",
  },
  {
    id: "t2",
    reference: "TXN-77BD3E10",
    merchant_id: "m2",
    merchant_name: "Mzuzu Fresh Market",
    branch_name: "Main Branch",
    till_name: "Till 2",
    amount: "1200.00",
    currency: "MWK",
    status: "pending",
    provider_name: "TNM Mpamba",
    created_at: "2026-08-30T08:01:00Z",
    completed_at: null,
  },
  {
    id: "t3",
    reference: "TXN-1A44F0E9",
    merchant_id: "m1",
    merchant_name: "Chikondi General Store",
    branch_name: "Area 47 Branch",
    till_name: "Front Counter",
    amount: "800.00",
    currency: "MWK",
    status: "failed",
    provider_name: "Airtel Money",
    created_at: "2026-08-29T18:44:00Z",
    completed_at: "2026-08-29T18:44:11Z",
  },
];

export type OpsPeriod = "24h" | "7d" | "30d";

export interface VolumePoint {
  label: string;
  volume: number;
  count: number;
  failed: number;
}

/** Illustrative series for dashboard visualization — not live ledger data. */
export const mockVolumeSeries: Record<OpsPeriod, VolumePoint[]> = {
  "24h": [
    { label: "00", volume: 420_000, count: 18, failed: 1 },
    { label: "02", volume: 180_000, count: 7, failed: 0 },
    { label: "04", volume: 95_000, count: 4, failed: 0 },
    { label: "06", volume: 260_000, count: 11, failed: 1 },
    { label: "08", volume: 890_000, count: 34, failed: 2 },
    { label: "10", volume: 1_240_000, count: 41, failed: 1 },
    { label: "12", volume: 1_560_000, count: 52, failed: 3 },
    { label: "14", volume: 1_310_000, count: 47, failed: 2 },
    { label: "16", volume: 1_720_000, count: 58, failed: 2 },
    { label: "18", volume: 1_050_000, count: 39, failed: 1 },
    { label: "20", volume: 640_000, count: 22, failed: 1 },
    { label: "22", volume: 410_000, count: 15, failed: 0 },
  ],
  "7d": [
    { label: "Tue", volume: 6_200_000, count: 210, failed: 8 },
    { label: "Wed", volume: 7_400_000, count: 248, failed: 9 },
    { label: "Thu", volume: 6_900_000, count: 231, failed: 6 },
    { label: "Fri", volume: 8_100_000, count: 276, failed: 11 },
    { label: "Sat", volume: 5_400_000, count: 188, failed: 5 },
    { label: "Sun", volume: 4_200_000, count: 142, failed: 4 },
    { label: "Mon", volume: 7_800_000, count: 259, failed: 7 },
  ],
  "30d": [
    { label: "W1", volume: 32_000_000, count: 1100, failed: 28 },
    { label: "W2", volume: 36_500_000, count: 1240, failed: 31 },
    { label: "W3", volume: 33_200_000, count: 1188, failed: 22 },
    { label: "W4", volume: 41_800_000, count: 1410, failed: 34 },
  ],
};

export interface NetworkProvider {
  code: string;
  name: string;
  status: "operational" | "degraded" | "sandbox";
  availability: string;
  capabilities: string[];
  lastActivity: string;
}

export const mockNetworkProviders: NetworkProvider[] = [
  {
    code: "airtel_money",
    name: "Airtel Money",
    status: "operational",
    availability: "99.4%",
    capabilities: ["Push", "Status"],
    lastActivity: "2 min ago",
  },
  {
    code: "tnm_mpamba",
    name: "TNM Mpamba",
    status: "degraded",
    availability: "97.1%",
    capabilities: ["Push", "Status"],
    lastActivity: "11 min ago",
  },
  {
    code: "national_bank",
    name: "National Bank",
    status: "sandbox",
    availability: "—",
    capabilities: ["Push"],
    lastActivity: "No live traffic",
  },
  {
    code: "simulated",
    name: "Simulated rail",
    status: "sandbox",
    availability: "100%",
    capabilities: ["Push", "Status", "Cancel"],
    lastActivity: "Just now",
  },
];

export interface SystemNode {
  name: string;
  state: "healthy" | "degraded" | "down" | "unknown";
  detail: string;
}

export const mockSystemNodes: SystemNode[] = [
  { name: "Backend", state: "healthy", detail: "API process" },
  { name: "PostgreSQL", state: "healthy", detail: "Primary" },
  { name: "Redis", state: "healthy", detail: "Broker / cache" },
  { name: "Celery", state: "unknown", detail: "No live probe in preview" },
  { name: "Providers", state: "degraded", detail: "Sandbox + one rail lag" },
];


/**
 * Demo-mode identity for visual review. Uses the existing mock platform
 * admin (`role_id: "r1"`) so `usePermissions()` resolves the mock catalog.
 * Never used as a production credential.
 */
export function getDemoAdminUser(): AuthenticatedUser {
  const admin = mockUsers.find((user) => user.role_id === "r1" && user.is_active);
  if (!admin) {
    throw new Error("Demo admin is missing from the mock catalog");
  }
  return {
    id: admin.id,
    email: admin.email,
    full_name: admin.full_name,
    merchant_id: admin.merchant_id,
    branch_id: admin.branch_id,
    role_id: admin.role_id,
    is_active: admin.is_active,
  };
}
