import type { PaymentProvider } from "@/lib/types/payment";

export type ProviderLifecycle =
  | "LIVE"
  | "SIMULATED"
  | "DISABLED"
  | "UNAVAILABLE"
  | "CONTRACT NOT READY"
  | "DEGRADED";

export function providerLifecycle(provider: PaymentProvider): ProviderLifecycle {
  if (provider.is_simulated) {
    return "SIMULATED";
  }
  if (!provider.live_contract_ready) {
    return "CONTRACT NOT READY";
  }
  if (!provider.is_active) {
    return "DISABLED";
  }
  if (provider.health_state === "unavailable") {
    return "UNAVAILABLE";
  }
  if (provider.health_state === "degraded") {
    return "DEGRADED";
  }
  return "LIVE";
}

export function providerLifecycleTone(
  state: ProviderLifecycle,
): "success" | "warning" | "error" | "neutral" | "info" {
  if (state === "LIVE") return "success";
  if (state === "SIMULATED") return "info";
  if (state === "DEGRADED") return "warning";
  if (state === "DISABLED" || state === "CONTRACT NOT READY") return "neutral";
  return "error";
}

/** A live operational rail — not simulated and not merely catalogued. */
export function isOperationalLiveRail(provider: PaymentProvider): boolean {
  return providerLifecycle(provider) === "LIVE" || providerLifecycle(provider) === "DEGRADED";
}
