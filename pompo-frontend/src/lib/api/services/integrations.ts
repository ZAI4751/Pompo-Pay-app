import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type {
  IntegrationClient,
  IntegrationClientCreate,
  IntegrationClientCreated,
  OutboundWebhookDelivery,
} from "@/lib/types/integration";

const DEMO_UNAVAILABLE: ApiResult<never> = {
  status: "error",
  kind: "unavailable",
  message: "Demo mode cannot manage integration clients. Sign in against the backend.",
};

export const integrationsService = {
  async list(merchantId?: string): Promise<ApiResult<IntegrationClient[]>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    const query = merchantId ? `?merchant_id=${encodeURIComponent(merchantId)}` : "";
    return apiRequest<IntegrationClient[]>(`/integrations/clients${query}`);
  },

  async get(clientId: string): Promise<ApiResult<IntegrationClient>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest<IntegrationClient>(`/integrations/clients/${encodeURIComponent(clientId)}`);
  },

  async create(payload: IntegrationClientCreate): Promise<ApiResult<IntegrationClientCreated>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest<IntegrationClientCreated>("/integrations/clients", {
      method: "POST",
      body: payload,
    });
  },

  async update(
    clientId: string,
    payload: {
      name?: string;
      webhook_url?: string | null;
      disabled?: boolean;
      scopes?: string[];
    },
  ): Promise<ApiResult<IntegrationClient>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest<IntegrationClient>(`/integrations/clients/${encodeURIComponent(clientId)}`, {
      method: "PATCH",
      body: payload,
    });
  },

  async rotateKey(clientId: string): Promise<ApiResult<{ client_id: string; key_prefix: string; api_key: string }>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest(`/integrations/clients/${encodeURIComponent(clientId)}/keys`, {
      method: "POST",
    });
  },

  async revoke(clientId: string): Promise<ApiResult<IntegrationClient>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest<IntegrationClient>(
      `/integrations/clients/${encodeURIComponent(clientId)}/revoke`,
      { method: "POST" },
    );
  },

  async listDeliveries(clientId: string): Promise<ApiResult<OutboundWebhookDelivery[]>> {
    if (USE_MOCKS) return DEMO_UNAVAILABLE;
    return apiRequest<OutboundWebhookDelivery[]>(
      `/integrations/clients/${encodeURIComponent(clientId)}/deliveries`,
    );
  },
};
