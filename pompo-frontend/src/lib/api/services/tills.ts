import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Till, TillCreate, TillUpdate } from "@/lib/types/merchant";
import { mockTills } from "@/mocks/data";

const LATENCY_MS = 300;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
}

export const tillsService = {
  async list(branchId: string): Promise<ApiResult<Till[]>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "success",
        data: mockTills.filter((till) => till.branch_id === branchId),
      };
    }
    return apiRequest<Till[]>(`/organization/branches/${branchId}/tills`);
  },

  async get(tillId: string): Promise<ApiResult<Till>> {
    if (USE_MOCKS) {
      await delay();
      const till = mockTills.find((item) => item.id === tillId);
      if (!till) {
        return { status: "error", kind: "not_found", message: "Till not found", httpStatus: 404 };
      }
      return { status: "success", data: till };
    }
    return apiRequest<Till>(`/organization/tills/${tillId}`);
  },

  async create(branchId: string, payload: TillCreate): Promise<ApiResult<Till>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist tills. Sign in against the backend.",
      };
    }
    return apiRequest<Till>(`/organization/branches/${branchId}/tills`, {
      method: "POST",
      body: payload,
    });
  },

  async update(tillId: string, payload: TillUpdate): Promise<ApiResult<Till>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist tills. Sign in against the backend.",
      };
    }
    return apiRequest<Till>(`/organization/tills/${tillId}`, { method: "PATCH", body: payload });
  },

  async remove(tillId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist tills. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/organization/tills/${tillId}`, { method: "DELETE" });
  },
};
