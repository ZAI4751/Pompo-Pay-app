/** MOCK service -- see merchants.ts for the pattern this follows. */

import type { ApiResult } from "@/lib/types/common";
import type { Role, RoleDetail } from "@/lib/types/rbac";
import { mockRoleDetails, mockRoles } from "@/mocks/data";

const LATENCY_MS = 300;

export const rolesService = {
  async list(): Promise<ApiResult<Role[]>> {
    await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
    return { status: "success", data: mockRoles };
  },

  async get(id: string): Promise<ApiResult<RoleDetail>> {
    await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
    const role = mockRoleDetails[id];
    if (!role) {
      return {
        status: "error",
        kind: "not_found",
        message: "Role not found",
        httpStatus: 404,
      };
    }
    return { status: "success", data: role };
  },
};
