/**
 * Central environment configuration for the Master Admin.
 *
 * Never hardcode production API URLs in source. Vercel injects
 * NEXT_PUBLIC_* values at build time; local development uses .env.local.
 */

export type DeployEnvironment = "local" | "preview" | "production";

function normalizeBaseUrl(url: string): string {
  return url.replace(/\/+$/, "");
}

function resolveDeployEnvironment(): DeployEnvironment {
  const vercelEnv = process.env.VERCEL_ENV;
  if (vercelEnv === "production") return "production";
  if (vercelEnv === "preview") return "preview";
  return "local";
}

function assertProductionApiUrl(url: string): void {
  if (/^http:\/\/(localhost|127\.0\.0\.1)/i.test(url)) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL must not point to localhost in production. See docs/admin-deployment.md",
    );
  }
  if (!/^https:\/\//i.test(url)) {
    throw new Error(
      "NEXT_PUBLIC_API_BASE_URL must use HTTPS in production. See docs/admin-deployment.md",
    );
  }
}

function resolveApiBaseUrl(deployEnv: DeployEnvironment): string {
  const fromEnv = process.env.NEXT_PUBLIC_API_BASE_URL?.trim();

  if (fromEnv) {
    const normalized = normalizeBaseUrl(fromEnv);
    if (deployEnv === "production") {
      assertProductionApiUrl(normalized);
    }
    return normalized;
  }

  if (deployEnv === "local") {
    return "http://localhost:8000/api/v1";
  }

  throw new Error(
    "NEXT_PUBLIC_API_BASE_URL is required for Vercel preview and production deployments. See docs/admin-deployment.md",
  );
}

function resolveUseMocks(deployEnv: DeployEnvironment): boolean {
  const requested = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
  if (deployEnv === "production" && requested) {
    throw new Error(
      "NEXT_PUBLIC_USE_MOCKS cannot be enabled in Vercel production. See docs/admin-deployment.md",
    );
  }
  return requested && deployEnv !== "production";
}

/** Where this build runs: local machine, Vercel preview, or Vercel production. */
export const DEPLOY_ENV = resolveDeployEnvironment();

/** FastAPI /api/v1 base URL — environment-driven, never hardcoded for prod. */
export const API_BASE_URL = resolveApiBaseUrl(DEPLOY_ENV);

/**
 * Demo fixtures and passwordless demo login. Disabled on Vercel production
 * even if the env var is mis-set. Live auth always uses the real backend.
 */
export const USE_MOCKS = resolveUseMocks(DEPLOY_ENV);

export const IS_PRODUCTION_DEPLOY = DEPLOY_ENV === "production";
