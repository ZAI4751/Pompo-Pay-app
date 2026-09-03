/**
 * Mirrors payment status values on GET /payments and GET /payments/{reference}.
 * Payments are the transaction record. Money is always a decimal string.
 */

export type TransactionStatus =
  | "created"
  | "qr_generated"
  | "pending"
  | "pending_user_pin"
  | "processing"
  | "success"
  | "failed"
  | "timeout"
  | "cancelled"
  | "refunded";

export interface Transaction {
  id: string;
  reference: string;
  merchant_id: string;
  merchant_name: string;
  branch_name: string;
  till_name: string;
  amount: string;
  currency: string;
  status: TransactionStatus;
  provider_name: string | null;
  created_at: string;
  completed_at: string | null;
}
