/**
 * User directory is not implemented on the backend (no list/CRUD).
 * Role assignment exists at PUT /rbac/users/{id}/role — see rolesService.
 */

import { USE_MOCKS } from "../config";
import type { ApiResult, Paginated } from "@/lib/types/common";
import type { StaffUser } from "@/lib/types/staff-user";
import { mockUsers } from "@/mocks/data";

export const usersService = {
  async list(): Promise<ApiResult<Paginated<StaffUser>>> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, 300));
      return {
        status: "success",
        data: { items: mockUsers, total: mockUsers.length, page: 1, pageSize: 20 },
      };
    }
    return {
      status: "error",
      kind: "unavailable",
      message:
        "User list and user CRUD are not implemented on the backend. Role assignment exists at PUT /api/v1/rbac/users/{user_id}/role.",
      httpStatus: 503,
    };
  },
};
