import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";

export interface AdminPaymentMethod {
  id: string;
  provider_code: string;
  provider_display_name: string;
  instrument_type: string;
  display_name: string;
  masked_identifier: string;
  status: string;
  is_default: boolean;
  is_sandbox: boolean;
  last_used_at: string | null;
  created_at: string;
  customer_email: string | null;
}

export const instrumentsService = {
  async adminList(): Promise<ApiResult<AdminPaymentMethod[]>> {
    if (USE_MOCKS) {
      return { status: "success", data: [] };
    }
    return apiRequest<AdminPaymentMethod[]>("/payment-methods/admin");
  },
};
