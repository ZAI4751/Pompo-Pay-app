import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";

export interface CustomerStats {
  customer_count: number;
  payment_requests: Record<string, number>;
  support_open_count: number;
}

export interface SupportRequest {
  id: string;
  public_identifier: string;
  category: string;
  subject: string;
  message: string;
  payment_reference: string | null;
  status: string;
  created_at: string | null;
}

export interface PaymentRequestRow {
  id: string;
  public_identifier: string;
  merchant_name: string | null;
  amount: string;
  currency: string;
  status: string;
  payment_reference: string | null;
  created_at: string | null;
}

export const customersService = {
  async stats(): Promise<ApiResult<CustomerStats>> {
    if (USE_MOCKS) {
      return {
        status: "success",
        data: { customer_count: 0, payment_requests: {}, support_open_count: 0 },
      };
    }
    return apiRequest<CustomerStats>("/customers/stats");
  },

  async supportRequests(): Promise<ApiResult<SupportRequest[]>> {
    if (USE_MOCKS) {
      return { status: "success", data: [] };
    }
    return apiRequest<SupportRequest[]>("/support-requests");
  },

  async paymentRequests(): Promise<ApiResult<PaymentRequestRow[]>> {
    if (USE_MOCKS) {
      return { status: "success", data: [] };
    }
    return apiRequest<PaymentRequestRow[]>("/payment-requests");
  },
};
