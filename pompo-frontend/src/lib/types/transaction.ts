/**
 * Mirrors app/models/payment.py's TransactionStatus enum exactly. The
 * transaction API itself does not exist on the backend yet (payment
 * milestones are future work) -- this type exists so the Transactions
 * screen's table/filter UI is ready to receive real data later without
 * a redesign. Money is always a decimal string, never a float, matching
 * how the backend stores it (Numeric(18,2)) -- never do float arithmetic
 * on amount in this codebase.
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
