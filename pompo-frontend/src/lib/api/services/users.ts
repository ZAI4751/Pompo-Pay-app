/** MOCK service -- see merchants.ts for the pattern this follows. */

import type { ApiResult, Paginated } from "@/lib/types/common";
import type { StaffUser } from "@/lib/types/staff-user";
import { mockUsers } from "@/mocks/data";

const LATENCY_MS = 300;

export const usersService = {
  async list(): Promise<ApiResult<Paginated<StaffUser>>> {
    await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
    return {
      status: "success",
      data: { items: mockUsers, total: mockUsers.length, page: 1, pageSize: 20 },
    };
  },
};
