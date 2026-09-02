export interface SettlementRecord {
  id: string;
  public_identifier: string;
  batch_id: string;
  provider_id: string;
  provider_settlement_reference: string;
  transaction_id: string | null;
  payment_attempt_id: string | null;
  merchant_id: string | null;
  branch_id: string | null;
  payment_reference: string | null;
  provider_transaction_reference: string | null;
  gross_amount: string;
  provider_fee: string;
  pompo_fee: string;
  merchant_net: string;
  currency: string;
  status: string;
  settlement_date: string;
  received_at: string;
  created_at: string;
  updated_at: string;
  reconciliation: ReconciliationRecord | null;
}

export interface SettlementBatchRecord {
  id: string;
  public_identifier: string;
  provider_id: string;
  external_batch_reference: string;
  settlement_date: string;
  currency: string;
  record_count: number;
  total_gross: string;
  total_provider_fees: string;
  total_pompo_fees: string;
  total_merchant_net: string;
  status: string;
  created_at: string;
  processed_at: string | null;
}

export interface ReconciliationRecord {
  id: string;
  public_identifier: string;
  settlement_id: string | null;
  transaction_id: string | null;
  status: string;
  mismatch_category: string | null;
  expected_amount: string | null;
  actual_amount: string | null;
  variance: string | null;
  expected_provider_fee: string | null;
  actual_provider_fee: string | null;
  expected_pompo_fee: string | null;
  actual_pompo_fee: string | null;
  expected_currency: string | null;
  actual_currency: string | null;
  pompo_reference: string | null;
  provider_reference: string | null;
  detected_at: string;
  resolved_at: string | null;
  resolution_note: string | null;
}

export interface SettlementSummary {
  total_settlements: number;
  total_gross: string;
  total_provider_fees: string;
  total_pompo_fees: string;
  total_merchant_net: string;
}

export interface ReconciliationSummary extends SettlementSummary {
  matched: number;
  partial_match: number;
  unmatched: number;
  discrepancy: number;
  investigation: number;
  resolved: number;
  matched_rate: string;
  unmatched_count: number;
  discrepancy_total: string;
}

export interface ReconciliationRunRecord {
  id: string;
  public_identifier: string;
  provider_id: string | null;
  window_start: string;
  window_end: string;
  records_examined: number;
  matched_count: number;
  unmatched_count: number;
  discrepancy_count: number;
  partial_count: number;
  investigation_count: number;
  total_expected: string;
  total_actual: string;
  total_variance: string;
  status: string;
  started_at: string | null;
  finished_at: string | null;
}
