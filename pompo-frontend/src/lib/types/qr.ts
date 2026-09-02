/** QR payment types aligned with /api/v1/qr contracts. */

export type QRType = "static" | "dynamic";
export type QRStatus = "active" | "disabled" | "revoked" | "expired" | "consumed";

export interface QRCodeRecord {
  public_identifier: string;
  qr_type: QRType;
  version: number;
  status: QRStatus;
  encoded_payload: string;
  merchant_id: string;
  branch_id: string;
  till_id: string;
  merchant_name: string;
  branch_name: string;
  till_name: string;
  amount: string | null;
  currency: string;
  payment_reference: string | null;
  expires_at: string | null;
  created_at: string;
  revoked_at: string | null;
}

export interface QRInspect {
  public_identifier: string;
  qr_type: QRType;
  version: number;
  status: QRStatus;
  merchant_name: string;
  branch_name: string;
  till_name: string;
  amount: string | null;
  currency: string;
  payment_reference: string | null;
  expires_at: string | null;
}

export interface StaticQRCreatePayload {
  merchant_id: string;
  branch_id: string;
  till_id: string;
}

export interface DynamicQRCreatePayload {
  merchant_id: string;
  branch_id: string;
  till_id: string;
  amount: string;
  currency?: string;
  payment_method?: string;
  provider_code?: string;
  customer_phone?: string;
  description?: string;
  expires_in_seconds?: number;
  idempotency_key: string;
}

export interface PaymentFromQRPayload {
  payload: string;
  idempotency_key: string;
  amount?: string;
  payment_method?: string;
  provider_code?: string;
  customer_phone?: string;
  description?: string;
}
