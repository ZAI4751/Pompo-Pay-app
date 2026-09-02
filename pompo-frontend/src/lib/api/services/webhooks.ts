import { apiRequest } from "../client";
import type { ApiResult } from "@/lib/types/common";
import type { WebhookEventRecord } from "@/lib/types/webhook";

export interface WebhookListFilters {
  provider_code?: string;
  processing_status?: string;
  event_type?: string;
  payment_reference?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(filters: WebhookListFilters = {}): string {
  const params = new URLSearchParams();
  if (filters.provider_code) params.set("provider_code", filters.provider_code);
  if (filters.processing_status) params.set("processing_status", filters.processing_status);
  if (filters.event_type) params.set("event_type", filters.event_type);
  if (filters.payment_reference) params.set("payment_reference", filters.payment_reference);
  if (filters.limit !== undefined) params.set("limit", String(filters.limit));
  if (filters.offset !== undefined) params.set("offset", String(filters.offset));
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const webhooksService = {
  async list(filters: WebhookListFilters = {}): Promise<ApiResult<WebhookEventRecord[]>> {
    return apiRequest<WebhookEventRecord[]>(`/webhooks${buildQuery(filters)}`);
  },

  async get(eventId: string): Promise<ApiResult<WebhookEventRecord>> {
    return apiRequest<WebhookEventRecord>(`/webhooks/events/${encodeURIComponent(eventId)}`);
  },
};
