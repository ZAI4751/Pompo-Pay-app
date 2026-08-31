/**
 * Typed mock/demo data. Nothing here is presented as real backend data --
 * every screen that reads from this file also renders a visible "Demo
 * data" indicator (see components/ui/MockDataBadge.tsx).
 */

import type { Permission, Role, RoleDetail } from "@/lib/types/rbac";
import type { Merchant } from "@/lib/types/merchant";
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
    permission_count: mockPermissions.length,
    user_count: 2,
    created_at: "2026-06-01T09:00:00Z",
  },
  {
    id: "r2",
    code: "merchant_owner",
    name: "Merchant Owner",
    description: "Full access within a single merchant.",
    is_system_role: true,
    permission_count: 7,
    user_count: 14,
    created_at: "2026-06-01T09:00:00Z",
  },
  {
    id: "r3",
    code: "branch_manager",
    name: "Branch Manager",
    description: "Manages a branch's tills and staff.",
    is_system_role: true,
    permission_count: 4,
    user_count: 31,
    created_at: "2026-06-01T09:00:00Z",
  },
  {
    id: "r4",
    code: "cashier",
    name: "Cashier",
    description: "Processes transactions at a till.",
    is_system_role: true,
    permission_count: 2,
    user_count: 122,
    created_at: "2026-06-01T09:00:00Z",
  },
  {
    id: "r5",
    code: "regional_auditor",
    name: "Regional Auditor",
    description: "Custom role: read-only access for compliance reviews.",
    is_system_role: false,
    permission_count: 3,
    user_count: 3,
    created_at: "2026-07-14T11:30:00Z",
  },
];

export const mockRoleDetails: Record<string, RoleDetail> = Object.fromEntries(
  mockRoles.map((role) => [
    role.id,
    { ...role, permissions: mockPermissions.slice(0, role.permission_count) },
  ]),
);

export const mockMerchants: Merchant[] = [
  {
    id: "m1",
    name: "Chikondi General Store",
    legal_name: "Chikondi Enterprises Ltd",
    contact_email: "owner@chikondi.mw",
    contact_phone: "+265 991 000 001",
    is_active: true,
    branch_count: 3,
    created_at: "2026-05-12T08:00:00Z",
  },
  {
    id: "m2",
    name: "Mzuzu Fresh Market",
    legal_name: "Mzuzu Fresh Market Ltd",
    contact_email: "admin@mzuzufresh.mw",
    contact_phone: "+265 991 222 333",
    is_active: true,
    branch_count: 1,
    created_at: "2026-06-02T08:00:00Z",
  },
  {
    id: "m3",
    name: "Lilongwe Pharmacy Group",
    legal_name: "LPG Holdings",
    contact_email: "finance@lpg.mw",
    contact_phone: "+265 888 444 555",
    is_active: false,
    branch_count: 6,
    created_at: "2026-04-20T08:00:00Z",
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
