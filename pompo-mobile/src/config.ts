import Constants from "expo-constants";

const extra = (Constants.expoConfig?.extra ?? {}) as { apiBaseUrl?: string };

const PRODUCTION_API = "https://pompo-api-production.up.railway.app/api/v1";

/**
 * Resolve the API host for Expo Go / simulators.
 * Physical phones cannot reach `localhost` on the developer machine — use the
 * same LAN address Metro already advertises (e.g. 192.168.x.x:8081).
 */
export function resolveDevApiBaseUrl(hostUri?: string | null): string {
  const host = hostUri?.split(":")[0]?.trim();
  if (host && host !== "localhost" && host !== "127.0.0.1") {
    return `http://${host}:8000/api/v1`;
  }
  return "http://localhost:8000/api/v1";
}

function resolveApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  if (__DEV__) {
    const hostUri =
      Constants.expoConfig?.hostUri ??
      Constants.expoGoConfig?.debuggerHost ??
      null;
    return resolveDevApiBaseUrl(hostUri);
  }
  return (extra.apiBaseUrl ?? PRODUCTION_API).replace(/\/$/, "");
}

export const API_BASE_URL = resolveApiBaseUrl();

if (__DEV__) {
  // Visible in the Metro terminal when the bundle loads — helps Expo Go debugging.
  console.log(`[POMPO] API_BASE_URL=${API_BASE_URL}`);
}
