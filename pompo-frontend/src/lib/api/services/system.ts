import { apiRequest } from "../client";
import { USE_MOCKS } from "../config";
import type { ApiResult } from "@/lib/types/common";
import type { PlatformConfig } from "@/lib/types/system";

const LIVE_REQUIRED: ApiResult<never> = {
  status: "error",
  kind: "unavailable",
  message: "Platform configuration is only available against the live API. Sign in to a backend session.",
};

export const systemService = {
  async config(): Promise<ApiResult<PlatformConfig>> {
    if (USE_MOCKS) return LIVE_REQUIRED;
    return apiRequest<PlatformConfig>("/system/config");
  },
};
