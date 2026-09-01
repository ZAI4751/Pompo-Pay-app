import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Permission, Role, RoleCreate, RoleDetail, RoleUpdate } from "@/lib/types/rbac";
import { mockPermissions, mockRoleDetails, mockRoles } from "@/mocks/data";

const LATENCY_MS = 300;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
}

function toDetail(role: Role, catalog: Permission[]): RoleDetail {
  const permissions = catalog.filter((permission) => role.permission_codes.includes(permission.code));
  return { ...role, permissions };
}

export const rolesService = {
  async list(): Promise<ApiResult<Role[]>> {
    if (USE_MOCKS) {
      await delay();
      return { status: "success", data: mockRoles };
    }
    return apiRequest<Role[]>("/rbac/roles");
  },

  async get(id: string): Promise<ApiResult<RoleDetail>> {
    if (USE_MOCKS) {
      await delay();
      const role = mockRoleDetails[id];
      if (!role) {
        return { status: "error", kind: "not_found", message: "Role not found", httpStatus: 404 };
      }
      return { status: "success", data: role };
    }
    const [roleResult, catalogResult] = await Promise.all([
      apiRequest<Role>(`/rbac/roles/${id}`),
      apiRequest<Permission[]>("/rbac/permissions"),
    ]);
    if (roleResult.status === "error") return roleResult;
    const catalog = catalogResult.status === "success" ? catalogResult.data : [];
    return { status: "success", data: toDetail(roleResult.data, catalog) };
  },

  async create(payload: RoleCreate): Promise<ApiResult<Role>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist roles. Sign in against the backend.",
      };
    }
    return apiRequest<Role>("/rbac/roles", { method: "POST", body: payload });
  },

  async update(roleId: string, payload: RoleUpdate): Promise<ApiResult<Role>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist roles. Sign in against the backend.",
      };
    }
    return apiRequest<Role>(`/rbac/roles/${roleId}`, { method: "PATCH", body: payload });
  },

  async remove(roleId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist roles. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/rbac/roles/${roleId}`, { method: "DELETE" });
  },

  async grantPermission(roleId: string, permissionId: string): Promise<ApiResult<{ permission_code: string }>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot grant permissions. Sign in against the backend.",
      };
    }
    return apiRequest(`/rbac/roles/${roleId}/permissions/${permissionId}`, { method: "POST" });
  },

  async revokePermission(roleId: string, permissionId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot revoke permissions. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/rbac/roles/${roleId}/permissions/${permissionId}`, {
      method: "DELETE",
    });
  },

  async assignUserRole(userId: string, roleId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot assign roles. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/rbac/users/${userId}/role`, {
      method: "PUT",
      body: { role_id: roleId },
    });
  },
};
