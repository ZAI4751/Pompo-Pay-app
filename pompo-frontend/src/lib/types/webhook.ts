export interface WebhookEventRecord {
  id: string;
  public_identifier: string;
  provider_id: string;
  provider_event_id: string;
  transaction_id: string | null;
  payment_attempt_id: string | null;
  event_type: string;
  event_version: string | null;
  payment_reference: string | null;
  provider_transaction_reference: string | null;
  received_at: string;
  processed_at: string | null;
  processing_status: string;
  processing_attempts: number;
  signature_verified: boolean;
  timestamp_validated: boolean;
  failure_category: string | null;
  failure_code: string | null;
  payload: Record<string, unknown>;
}
