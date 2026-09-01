/**
 * Mirrors app/schemas/rbac.py RoleResponse / PermissionResponse.
 */

export interface Permission {
  id: string;
  code: string;
  description: string | null;
}

export interface Role {
  id: string;
  code: string;
  name: string;
  description: string | null;
  is_system_role: boolean;
  is_active: boolean;
  permission_codes: string[];
}

export interface RoleCreate {
  code: string;
  name: string;
  description?: string | null;
}

export interface RoleUpdate {
  name?: string;
  description?: string | null;
  is_active?: boolean;
}

export interface RoleDetail extends Role {
  permissions: Permission[];
}
