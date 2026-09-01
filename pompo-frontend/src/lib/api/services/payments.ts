import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Payment, PaymentProvider } from "@/lib/types/payment";
import { providersService } from "./providers";

const LATENCY_MS = 300;

const LIST_UNAVAILABLE: ApiResult<never> = {
  status: "error",
  kind: "unavailable",
  message:
    "The backend has no payment list or search API. Retrieve a payment by its reference.",
  httpStatus: 503,
};

export const paymentsService = {
  async getByReference(reference: string): Promise<ApiResult<Payment>> {
    if (USE_MOCKS) {
      await new Promise((resolve) => setTimeout(resolve, LATENCY_MS));
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot look up live payments. Sign in against the backend.",
      };
    }
    return apiRequest<Payment>(`/payments/${encodeURIComponent(reference)}`);
  },

  async cancel(reference: string): Promise<ApiResult<Payment>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot cancel payments. Sign in against the backend.",
      };
    }
    return apiRequest<Payment>(`/payments/${encodeURIComponent(reference)}/cancel`, {
      method: "POST",
    });
  },

  async process(reference: string): Promise<ApiResult<Payment>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot process payments. Sign in against the backend.",
      };
    }
    return apiRequest<Payment>(`/payments/${encodeURIComponent(reference)}/process`, {
      method: "POST",
    });
  },

  async listProviders(): Promise<ApiResult<PaymentProvider[]>> {
    return providersService.list();
  },

  async updateProvider(
    code: string,
    payload: { is_active?: boolean; priority?: number },
  ): Promise<ApiResult<PaymentProvider>> {
    if (payload.is_active === true) {
      return providersService.enable(code);
    }
    if (payload.is_active === false) {
      return providersService.disable(code);
    }
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot change providers. Sign in against the backend.",
      };
    }
    return apiRequest<PaymentProvider>(`/providers/${encodeURIComponent(code)}`, {
      method: "PATCH",
      body: payload,
    });
  },

  listUnavailable(): ApiResult<never> {
    return LIST_UNAVAILABLE;
  },
};
