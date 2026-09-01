import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { HealthResponse, LivenessResponse, ReadinessResponse } from "@/lib/types/health";

export const healthService = {
  async check(): Promise<ApiResult<HealthResponse>> {
    if (USE_MOCKS) {
      return {
        status: "success",
        data: {
          status: "healthy",
          version: "demo",
          environment: "demo",
          response_time_ms: 0,
          components: {
            application: { status: "healthy", healthy: true },
            database: { status: "healthy", healthy: true },
            redis: { status: "healthy", healthy: true },
            celery: { status: "unknown", healthy: false, details: { note: "Demo fixture" } },
          },
        },
      };
    }
    return apiRequest<HealthResponse>("/health", { acceptStatuses: [503] });
  },

  async ready(): Promise<ApiResult<ReadinessResponse>> {
    if (USE_MOCKS) {
      return { status: "success", data: { ready: true, checks: { database: true, redis: true } } };
    }
    return apiRequest<ReadinessResponse>("/health/ready", { acceptStatuses: [503] });
  },

  async live(): Promise<ApiResult<LivenessResponse>> {
    if (USE_MOCKS) {
      return { status: "success", data: { alive: true } };
    }
    return apiRequest<LivenessResponse>("/health/live");
  },
};
