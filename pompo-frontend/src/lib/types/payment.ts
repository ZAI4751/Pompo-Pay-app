/** Mirrors app/schemas/payment.py payment and provider catalog contracts. */

export interface PaymentAttempt {
  id: string;
  attempt_number: number;
  status: string;
  provider_reference: string | null;
  provider_status: string | null;
  duration_ms: number | null;
  failure_code: string | null;
  retryable: boolean | null;
  failure_reason: string | null;
}

export interface Payment {
  id: string;
  reference: string;
  merchant_id: string;
  branch_id: string;
  till_id: string;
  amount: string;
  currency: string;
  payment_method: string;
  status: string;
  description: string | null;
  failure_reason: string | null;
  attempts: PaymentAttempt[];
}

export interface ProviderCapabilities {
  supports_push_payment: boolean;
  supports_status_query: boolean;
  supports_cancel: boolean;
  supports_refund: boolean;
  supports_webhooks: boolean;
  supports_qr: boolean;
  supports_payment_instruments?: boolean;
  supports_instrument_enroll?: boolean;
  supports_instrument_charge?: boolean;
  supports_instrument_verify?: boolean;
  supports_instrument_remove?: boolean;
}

export interface ProviderHealth {
  configured: boolean;
  reachable: boolean | null;
  supports_health_check: boolean;
  contract_ready: boolean;
  message: string | null;
}

export interface ProviderConfigurationStatus {
  base_url_configured: boolean;
  timeout_seconds: number;
  auth_configured: boolean;
  signing_configured: boolean;
  configuration_complete: boolean;
  rail_environment: string;
  production_rail_permitted: boolean;
  contract_registered: boolean;
}

export interface PaymentProvider {
  code: string;
  display_name: string;
  provider_type: string;
  is_active: boolean;
  is_simulated: boolean;
  environment: string;
  health_state: string;
  priority: number;
  supported_currencies: string[];
  supported_payment_methods: string[];
  capabilities: ProviderCapabilities;
  adapter_configured: boolean;
  live_contract_ready: boolean;
  configuration: ProviderConfigurationStatus;
  health: ProviderHealth;
}
