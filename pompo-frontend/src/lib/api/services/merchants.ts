/**
 * MOCK service -- the merchant management API doesn't exist on the
 * backend yet. Same ApiResult<T> shape as the real auth service, so
 * swapping this file's body for real apiRequest() calls later requires
 * no change to any component that consumes it.
 */

import type { ApiResult, Paginated } from "@/lib/types/common";
import type { Merchant } from "@/lib/types/merchant";
import { mockMerchants } from "@/mocks/data";

const LATENCY_MS = 300;

export const merchantsService = {
  async list(): Promise<ApiResult<Paginated<Merchant>>> {
    await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
    return {
      status: "success",
      data: { items: mockMerchants, total: mockMerchants.length, page: 1, pageSize: 20 },
    };
  },
};
