import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Merchant, MerchantCreate, MerchantUpdate } from "@/lib/types/merchant";
import { mockMerchants } from "@/mocks/data";

const LATENCY_MS = 300;

function delay(): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
}

export const merchantsService = {
  async list(): Promise<ApiResult<Merchant[]>> {
    if (USE_MOCKS) {
      await delay();
      return { status: "success", data: mockMerchants };
    }
    return apiRequest<Merchant[]>("/organization/merchants");
  },

  async get(merchantId: string): Promise<ApiResult<Merchant>> {
    if (USE_MOCKS) {
      await delay();
      const merchant = mockMerchants.find((item) => item.id === merchantId);
      if (!merchant) {
        return { status: "error", kind: "not_found", message: "Merchant not found", httpStatus: 404 };
      }
      return { status: "success", data: merchant };
    }
    return apiRequest<Merchant>(`/organization/merchants/${merchantId}`);
  },

  async create(payload: MerchantCreate): Promise<ApiResult<Merchant>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist merchants. Sign in against the backend.",
      };
    }
    return apiRequest<Merchant>("/organization/merchants", { method: "POST", body: payload });
  },

  async update(merchantId: string, payload: MerchantUpdate): Promise<ApiResult<Merchant>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist merchants. Sign in against the backend.",
      };
    }
    return apiRequest<Merchant>(`/organization/merchants/${merchantId}`, {
      method: "PATCH",
      body: payload,
    });
  },

  async remove(merchantId: string): Promise<ApiResult<undefined>> {
    if (USE_MOCKS) {
      await delay();
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist merchants. Sign in against the backend.",
      };
    }
    return apiRequest<undefined>(`/organization/merchants/${merchantId}`, { method: "DELETE" });
  },
};
