/** Mirrors app/schemas/payment.py PaymentResponse and GET /payments/providers. */

export interface PaymentAttempt {
  id: string;
  attempt_number: number;
  status: string;
  provider_reference: string | null;
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
}

export interface PaymentProvider {
  code: string;
  display_name: string;
  is_active: boolean;
  is_simulated: boolean;
  environment: string;
  priority: number;
  supported_currencies: string[];
  supported_payment_methods: string[];
  capabilities: ProviderCapabilities;
  adapter_configured: boolean;
}
