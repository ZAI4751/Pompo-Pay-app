/** Central place reading environment configuration -- never hardcode a URL. */

export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

/**
 * When true, capabilities that have a live backend still return labeled
 * demo fixtures (visual review without Docker). When false (the control-
 * plane default), live capabilities call /api/v1 and unavailable ones
 * surface as missing APIs rather than fake records.
 *
 * See docs/admin-ui-architecture.md, "Mock/API boundary".
 */
export const USE_MOCKS = process.env.NEXT_PUBLIC_USE_MOCKS === "true";
