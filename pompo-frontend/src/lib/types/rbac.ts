/**
 * Mirrors the Role/Permission/RolePermission domain model from
 * pompo-backend M002/M004 (app/models/user.py). The listing/assignment
 * ENDPOINTS for these are still in development on the backend as of this
 * writing -- see docs/admin-ui-architecture.md, "Mock/API boundary" -- so
 * this app talks to them through the mock service layer only, using these
 * exact field shapes so swapping in the real HTTP calls later is a
 * same-shape drop-in.
 */

export interface Permission {
  id: string;
  code: string; // "<resource>:<action>", e.g. "users:read"
  description: string | null;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  permission_count: number;
  user_count: number;
  created_at: string;
}

export interface RoleDetail extends Role {
  permissions: Permission[];
}
