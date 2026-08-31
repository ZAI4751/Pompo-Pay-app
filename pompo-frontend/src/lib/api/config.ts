/** Central place reading environment configuration -- never hardcode a URL. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * When true, every service in src/lib/api/services/* returns from
 * src/mocks instead of calling the real backend, regardless of whether
 * API_BASE_URL is reachable. Flip off per-service (not globally) as each
 * backend milestone actually ships its endpoints -- see
 * docs/admin-ui-architecture.md, "Mock/API boundary".
 */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS !== "false";
