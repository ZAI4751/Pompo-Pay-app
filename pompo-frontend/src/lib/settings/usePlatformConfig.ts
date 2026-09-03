"use client";

import { useEffect, useState } from "react";
import { systemService } from "@/lib/api/services/system";
import type { PlatformConfig } from "@/lib/types/system";
import type { ApiResult } from "@/lib/types/common";

export function usePlatformConfig() {
  const [result, setResult] = useState<ApiResult<PlatformConfig> | null>(null);

  const load = () => {
    void systemService.config().then(setResult);
  };

  useEffect(() => {
    load();
  }, []);

  return { result, load, config: result?.status === "success" ? result.data : null };
}
