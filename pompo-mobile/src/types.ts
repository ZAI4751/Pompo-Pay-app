export type AppMode = "customer" | "merchant";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthenticatedUser {
  id: string;
  email: string;
  full_name: string;
  merchant_id: string | null;
  branch_id: string | null;
  role_id: string;
  role_code: string;
  is_active: boolean;
}

export interface QrInspect {
  public_identifier: string;
  qr_type: "static" | "dynamic" | string;
  version: number;
  status: string;
  merchant_name: string;
  branch_name: string;
  till_name: string;
  amount: string | null;
  currency: string;
  payment_reference: string | null;
  expires_at: string | null;
}

export interface QrRecord extends QrInspect {
  encoded_payload: string;
  merchant_id: string;
  branch_id: string;
  till_id: string;
  created_at: string;
  revoked_at: string | null;
}

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
  merchant_name: string | null;
  branch_name: string | null;
  till_name: string | null;
  created_at: string | null;
  completed_at: string | null;
}

export interface Merchant {
  id: string;
  name: string;
  legal_name: string | null;
  contact_email: string;
  contact_phone: string;
  is_active: boolean;
}

export interface Branch {
  id: string;
  merchant_id: string;
  name: string;
  address: string | null;
  is_active: boolean;
}

export interface Till {
  id: string;
  branch_id: string;
  merchant_id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export type ApiErrorKind =
  | "network"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "rate_limited"
  | "server"
  | "unavailable"
  | "unknown";

export interface ApiError {
  kind: ApiErrorKind;
  message: string;
  status?: number;
  requestId?: string;
  detail?: unknown;
}

export type ApiResult<T> = { ok: true; data: T; requestId?: string } | { ok: false; error: ApiError };
