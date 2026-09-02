import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { Payment } from "@/lib/types/payment";
import type {
  DynamicQRCreatePayload,
  PaymentFromQRPayload,
  QRCodeRecord,
  QRInspect,
  StaticQRCreatePayload,
} from "@/lib/types/qr";

export const qrService = {
  async createStatic(payload: StaticQRCreatePayload): Promise<ApiResult<QRCodeRecord>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot create QR codes. Sign in against the backend.",
      };
    }
    return apiRequest<QRCodeRecord>("/qr/static", { method: "POST", body: payload });
  },

  async createDynamic(payload: DynamicQRCreatePayload): Promise<ApiResult<QRCodeRecord>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot create QR codes. Sign in against the backend.",
      };
    }
    return apiRequest<QRCodeRecord>("/qr/dynamic", { method: "POST", body: payload });
  },

  async inspect(publicIdentifier: string): Promise<ApiResult<QRInspect>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot inspect QR codes. Sign in against the backend.",
      };
    }
    return apiRequest<QRInspect>(`/qr/${encodeURIComponent(publicIdentifier)}`);
  },

  async getAdmin(publicIdentifier: string): Promise<ApiResult<QRCodeRecord>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot load QR codes. Sign in against the backend.",
      };
    }
    return apiRequest<QRCodeRecord>(
      `/qr/${encodeURIComponent(publicIdentifier)}/admin`,
    );
  },

  async revoke(publicIdentifier: string): Promise<ApiResult<QRCodeRecord>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot revoke QR codes. Sign in against the backend.",
      };
    }
    return apiRequest<QRCodeRecord>(
      `/qr/${encodeURIComponent(publicIdentifier)}/revoke`,
      { method: "POST" },
    );
  },

  async payFromQR(payload: PaymentFromQRPayload): Promise<ApiResult<Payment>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot initiate QR payments. Sign in against the backend.",
      };
    }
    return apiRequest<Payment>("/payments/from-qr", { method: "POST", body: payload });
  },
};
