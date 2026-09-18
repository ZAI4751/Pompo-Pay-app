import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";

export interface PaymentRequest {
  id: string;
  public_identifier: string;
  share_code: string;
  requester_id: string;
  requester_name?: string | null;
  payer_user_id?: string | null;
  merchant_id?: string | null;
  merchant_name?: string | null;
  branch_name?: string | null;
  till_name?: string | null;
  amount: number | string;
  currency: string;
  description?: string | null;
  status: "pending" | "paid" | "cancelled" | "expired";
  expires_at?: string | null;
  paid_at?: string | null;
  payment_reference?: string | null;
  bill_split_id?: string | null;
  created_at?: string | null;
}

export const paymentRequestsService = {
  async listMine(
    status?: string,
    limit = 50,
    offset = 0,
  ): Promise<ApiResult<PaymentRequest[]>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot list payment requests. Sign in against the backend.",
      };
    }
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    params.set("limit", String(limit));
    params.set("offset", String(offset));
    return apiRequest<PaymentRequest[]>(`/payment-requests?${params.toString()}`);
  },

  async cancel(publicIdentifier: string): Promise<ApiResult<PaymentRequest>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot cancel payment requests.",
      };
    }
    return apiRequest<PaymentRequest>(
      `/payment-requests/${encodeURIComponent(publicIdentifier)}/cancel`,
      { method: "POST" },
    );
  },
};
