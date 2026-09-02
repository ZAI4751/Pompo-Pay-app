import Constants from "expo-constants";

const extra = (Constants.expoConfig?.extra ?? {}) as { apiBaseUrl?: string };

const PRODUCTION_API = "https://pompo-api-production.up.railway.app/api/v1";

function resolveApiBaseUrl(): string {
  const fromEnv = process.env.EXPO_PUBLIC_API_BASE_URL?.trim();
  if (fromEnv) {
    return fromEnv.replace(/\/$/, "");
  }
  if (__DEV__) {
    return "http://localhost:8000/api/v1";
  }
  return (extra.apiBaseUrl ?? PRODUCTION_API).replace(/\/$/, "");
}

export const API_BASE_URL = resolveApiBaseUrl();
