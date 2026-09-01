import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Permission } from "@/lib/types/rbac";
import { mockPermissions } from "@/mocks/data";

const LATENCY_MS = 300;

export const permissionsService = {
  async list(): Promise<ApiResult<Permission[]>> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
      return { status: "success", data: mockPermissions };
    }
    return apiRequest<Permission[]>("/rbac/permissions");
  },

  async get(permissionId: string): Promise<ApiResult<Permission>> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
      const permission = mockPermissions.find((item) => item.id === permissionId);
      if (!permission) {
        return {
          status: "error",
          kind: "not_found",
          message: "Permission not found",
          httpStatus: 404,
        };
      }
      return { status: "success", data: permission };
    }
    return apiRequest<Permission>(`/rbac/permissions/${permissionId}`);
  },
};
