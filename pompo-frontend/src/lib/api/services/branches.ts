import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Branch, BranchCreate, BranchUpdate } from "@/lib/types/merchant";
import { mockBranches } from "@/mocks/data";

const LATENCY_MS = 300;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
}

export const branchesService = {
  async list(merchantId: string): Promise<ApiResult<Branch[]>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "success",
        data: mockBranches.filter((branch) => branch.merchant_id === merchantId),
      };
    }
    return apiRequest<Branch[]>(`/organization/merchants/${merchantId}/branches`);
  },

  async create(merchantId: string, payload: BranchCreate): Promise<ApiResult<Branch>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist branches. Sign in against the backend.",
      };
    }
    return apiRequest<Branch>(`/organization/merchants/${merchantId}/branches`, {
      method: "POST",
      body: payload,
    });
  },

  async update(branchId: string, payload: BranchUpdate): Promise<ApiResult<Branch>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist branches. Sign in against the backend.",
      };
    }
    return apiRequest<Branch>(`/organization/branches/${branchId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  async remove(branchId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist branches. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/organization/branches/${branchId}`, { method: "DELETE" });
  },
};
