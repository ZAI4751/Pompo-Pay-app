import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { PaymentProvider } from "@/lib/types/payment";

const MOCK_SIMULATED: PaymentProvider = {
  code: "simulated",
  display_name: "Simulated sandbox",
  provider_type: "simulated",
  is_active: true,
  is_simulated: true,
  environment: "sandbox",
  health_state: "active",
  priority: 1,
  supported_currencies: ["MWK"],
  supported_payment_methods: ["mobile_money"],
  capabilities: {
    supports_push_payment: true,
    supports_status_query: true,
    supports_cancel: true,
    supports_refund: false,
    supports_webhooks: false,
    supports_qr: false,
  },
  adapter_configured: true,
  live_contract_ready: true,
  configuration: {
    base_url_configured: true,
    timeout_seconds: 15,
    auth_configured: true,
    signing_configured: false,
    configuration_complete: true,
    rail_environment: "sandbox",
    production_rail_permitted: false,
    contract_registered: true,
  },
  health: {
    configured: true,
    reachable: true,
    supports_health_check: true,
    contract_ready: true,
    message: "Simulated adapter is local and deterministic",
  },
};

export const providersService = {
  async list(): Promise<ApiResult<PaymentProvider[]>> {
    if (USE_MOCKS) {
      return { status: "success", data: [MOCK_SIMULATED] };
    }
    return apiRequest<PaymentProvider[]>("/providers");
  },

  async get(code: string): Promise<ApiResult<PaymentProvider>> {
    if (USE_MOCKS) {
      return { status: "success", data: MOCK_SIMULATED };
    }
    return apiRequest<PaymentProvider>(`/providers/${encodeURIComponent(code)}`);
  },

  async enable(code: string): Promise<ApiResult<PaymentProvider>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot change providers. Sign in against the backend.",
      };
    }
    return apiRequest<PaymentProvider>(`/providers/${encodeURIComponent(code)}/enable`, {
      method: "POST",
    });
  },

  async disable(code: string): Promise<ApiResult<PaymentProvider>> {
    if (USE_MOCKS) {
      return {
        status: "error",
        kind: "unavailable",
        message: "Demo mode cannot change providers. Sign in against the backend.",
      };
    }
    return apiRequest<PaymentProvider>(`/providers/${encodeURIComponent(code)}/disable`, {
      method: "POST",
    });
  },

  async inspectHealth(code: string): Promise<ApiResult<PaymentProvider>> {
    if (USE_MOCKS) {
      return { status: "success", data: MOCK_SIMULATED };
    }
    return apiRequest<PaymentProvider>(`/providers/${encodeURIComponent(code)}/health`);
  },
};
