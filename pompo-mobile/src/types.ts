export type AppMode = "customer" | "merchant";

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  is_email_verified?: boolean;
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
  account_status?: "active" | "deactivated" | "suspended" | string;
  deactivated_at?: string | null;
  reactivated_at?: string | null;
  is_email_verified?: boolean;
  phone?: string | null;
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
  payment_url?: string | null;
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
  customer_status?: string | null;
  status_detail?: string | null;
  payment_instrument_id?: string | null;
  authorization_state?: string | null;
}

export interface PaymentMethod {
  id: string;
  provider_code: string;
  provider_display_name: string;
  instrument_type: string;
  display_name: string;
  masked_identifier: string;
  status: string;
  authorization_state: string;
  is_default: boolean;
  is_sandbox: boolean;
  last_used_at: string | null;
  created_at: string;
  unavailable_reason?: string | null;
}

export interface PaymentMethodCatalogItem {
  provider_code: string;
  instrument_type: string;
  label: string;
  available: boolean;
  is_sandbox: boolean;
  reason: string | null;
  authorization_state: string;
}

export interface PaymentReceipt {
  title: string;
  receipt_number: string;
  reference: string;
  merchant_name: string | null;
  branch_name: string | null;
  till_name: string | null;
  amount: string;
  currency: string;
  status: string;
  customer_status: string;
  status_detail: string;
  issued_at: string;
  completed_at: string | null;
  description: string | null;
  disclaimer: string;
}

export interface FavoriteMerchant {
  merchant_id: string;
  merchant_name: string;
  is_favorite: boolean;
  last_paid_at: string | null;
  last_payment_reference?: string | null;
  payment_count: number;
  is_active: boolean;
}

export interface PaymentRequest {
  id: string;
  public_identifier: string;
  share_code: string;
  requester_id: string;
  requester_name: string | null;
  payer_user_id: string | null;
  merchant_id: string;
  merchant_name: string | null;
  branch_name: string | null;
  till_name: string | null;
  amount: string;
  currency: string;
  description: string | null;
  status: string;
  expires_at: string | null;
  paid_at: string | null;
  payment_reference: string | null;
  bill_split_id: string | null;
  created_at: string | null;
}

export interface CustomerPreferences {
  notify_payment_success: boolean;
  notify_payment_failed: boolean;
  notify_payment_updates: boolean;
  notify_payment_requests: boolean;
  preferred_mode: string | null;
  phone_verification: string;
}

export interface CustomerInsight {
  payments_this_week: number;
  spent_this_week: string;
  payments_this_month: number;
  spent_this_month: string;
  payment_count: number;
  spent_total: string;
  most_used_merchants: { merchant_id: string; merchant_name: string; payment_count: number }[];
  disclaimer: string;
}

export interface AppNotification {
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
}

export interface NotificationList {
  unread_count: number;
  items: AppNotification[];
}

export interface SupportTicket {
  id: string;
  public_identifier: string;
  category: string;
  subject: string;
  message: string;
  payment_reference: string | null;
  status: string;
  created_at: string | null;
}

export interface MerchantSummary {
  merchant_id: string;
  payments_today: number;
  total_today: string;
  successful_all_time: number;
  currency: string;
}

export interface CustomerRegisterResponse extends TokenResponse {
  user_id: string;
  email: string;
  full_name: string;
  phone: string | null;
  role_code: string;
  phone_verification: string;
  is_email_verified?: boolean;
  email_verification?: string;
}

export interface AccessibleMerchant {
  id: string;
  name: string;
  legal_name?: string | null;
  is_active: boolean;
}

export interface AccessibleBranch {
  id: string;
  merchant_id: string;
  name: string;
  address?: string | null;
  is_active: boolean;
}

export interface AccessibleTill {
  id: string;
  branch_id: string;
  merchant_id: string;
  code: string;
  name: string;
  is_active: boolean;
}

export interface MerchantAccessResponse {
  allowed: boolean;
  reason: string | null;
  can_generate_qr: boolean;
  merchant: AccessibleMerchant | null;
  merchants: AccessibleMerchant[];
  branches: AccessibleBranch[];
  tills: AccessibleTill[];
  operating_branch_id: string | null;
  operating_till_id: string | null;
  permissions: string[];
}

export interface GenericSecurityResponse {
  detail: string;
  email_delivery: string;
}

export interface VerifyEmailResponse {
  detail: string;
  is_email_verified: boolean;
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
