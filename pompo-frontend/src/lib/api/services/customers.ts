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

export interface NotificationPreferences {
  notify_payment_success: boolean;
  notify_payment_failed: boolean;
  notify_payment_updates: boolean;
  notify_payment_requests: boolean;
  preferred_mode: string | null;
  phone_verification: string;
}

export interface NotificationInbox {
  unread_count: number;
  items: Array<{
    id: string;
    public_identifier: string;
    notification_type: string;
    title: string;
    body: string;
    entity_type: string | null;
    entity_id: string | null;
    payment_reference: string | null;
    read_at: string | null;
    created_at: string | null;
  }>;
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

  async preferences(): Promise<ApiResult<NotificationPreferences>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Notification preferences require a live backend session.",
      };
    }
    return apiRequest<NotificationPreferences>("/customers/me/preferences");
  },

  async updatePreferences(
    payload: Partial<
      Pick<
        NotificationPreferences,
        | "notify_payment_success"
        | "notify_payment_failed"
        | "notify_payment_updates"
        | "notify_payment_requests"
      >
    >,
  ): Promise<ApiResult<NotificationPreferences>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot persist notification preferences.",
      };
    }
    return apiRequest<NotificationPreferences>("/customers/me/preferences", {
      method: "PATCH",
      body: payload,
    });
  },

  async notifications(unreadOnly = false): Promise<ApiResult<NotificationInbox>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "The notification inbox requires a live backend session.",
      };
    }
    const query = unreadOnly ? "?unread_only=true" : "";
    return apiRequest<NotificationInbox>(`/notifications${query}`);
  },
};
