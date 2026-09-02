import { apiRequest } from "../client";
import type { ApiResult } from "@/lib/types/common";
import type {
  ReconciliationRecord,
  ReconciliationRunRecord,
  ReconciliationSummary,
  SettlementBatchRecord,
  SettlementRecord,
  SettlementSummary,
} from "@/lib/types/settlement";

export interface SettlementListFilters {
  provider_code?: string;
  status?: string;
  settlement_date?: string;
  batch_id?: string;
  limit?: number;
  offset?: number;
}

export interface ReconciliationListFilters {
  status?: string;
  provider_code?: string;
  run_id?: string;
  limit?: number;
  offset?: number;
}

function buildQuery(filters: object): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(filters)) {
    if (value !== undefined && value !== "") params.set(key, String(value));
  }
  const query = params.toString();
  return query ? `?${query}` : "";
}

export const settlementsService = {
  async list(filters: SettlementListFilters = {}): Promise<ApiResult<SettlementRecord[]>> {
    return apiRequest<SettlementRecord[]>(`/settlements${buildQuery(filters)}`);
  },

  async get(id: string): Promise<ApiResult<SettlementRecord>> {
    return apiRequest<SettlementRecord>(`/settlements/${encodeURIComponent(id)}`);
  },

  async listBatches(): Promise<ApiResult<SettlementBatchRecord[]>> {
    return apiRequest<SettlementBatchRecord[]>(`/settlements/batches`);
  },

  async summary(): Promise<ApiResult<SettlementSummary>> {
    return apiRequest<SettlementSummary>(`/settlements/summary`);
  },
};

export const reconciliationService = {
  async list(filters: ReconciliationListFilters = {}): Promise<ApiResult<ReconciliationRecord[]>> {
    return apiRequest<ReconciliationRecord[]>(`/reconciliation${buildQuery(filters)}`);
  },

  async get(id: string): Promise<ApiResult<ReconciliationRecord>> {
    return apiRequest<ReconciliationRecord>(`/reconciliation/${encodeURIComponent(id)}`);
  },

  async summary(): Promise<ApiResult<ReconciliationSummary>> {
    return apiRequest<ReconciliationSummary>(`/reconciliation/summary`);
  },

  async listRuns(): Promise<ApiResult<ReconciliationRunRecord[]>> {
    return apiRequest<ReconciliationRunRecord[]>(`/reconciliation/runs`);
  },

  async resolve(id: string, note: string): Promise<ApiResult<ReconciliationRecord>> {
    return apiRequest<ReconciliationRecord>(`/reconciliation/${encodeURIComponent(id)}/resolve`, {
      method: "POST",
      body: { note },
    });
  },
};
