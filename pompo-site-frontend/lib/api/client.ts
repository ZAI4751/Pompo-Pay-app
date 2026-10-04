/**
 * Centralized API client for the POMPO informational website.
 *
 * Connects the Next.js frontend to the FastAPI backend with:
 * - Unified base URL resolution from NEXT_PUBLIC_WEBSITE_API_URL
 * - Strongly-typed GET and POST methods without 'any'
 * - Clean error normalization (status code, detail messages)
 * - Configurable timeout with AbortController
 * - Support for Next.js fetch cache/revalidation options
 */

export class ApiClientError extends Error {
  readonly status: number;
  readonly statusText: string;
  readonly endpoint: string;
  readonly detail?: string;

  constructor(message: string, status: number, statusText: string, endpoint: string, detail?: string) {
    super(message);
    this.name = "ApiClientError";
    this.status = status;
    this.statusText = statusText;
    this.endpoint = endpoint;
    this.detail = detail;
  }
}

export interface RequestOptions {
  headers?: Record<string, string>;
  revalidate?: number | false;
  cache?: RequestCache;
  timeoutMs?: number;
}

export function getApiBaseUrl(): string {
  // NEXT_PUBLIC_WEBSITE_API_URL must be set to the production HTTPS backend URL
  // in the Vercel environment variables dashboard.
  // The "http://127.0.0.1:8000" fallback is a local-development convenience only
  // and is never reached in production where the env var is always defined.
  const url = process.env.NEXT_PUBLIC_WEBSITE_API_URL ?? "http://127.0.0.1:8000";
  // Strip trailing slashes and any trailing /api/v1 (paths append /api/v1)
  return url.replace(/\/+$/, "").replace(/\/api\/v1$/, "");
}

async function request<T>(
  path: string,
  method: "GET" | "POST",
  body?: unknown,
  options: RequestOptions = {}
): Promise<T> {
  const baseUrl = getApiBaseUrl();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  const fullUrl = `${baseUrl}${normalizedPath}`;

  const timeoutMs = options.timeoutMs ?? 10000;
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeoutMs);

  const headers: Record<string, string> = {
    Accept: "application/json",
    ...options.headers,
  };

  if (body !== undefined) {
    headers["Content-Type"] = "application/json";
  }

  const fetchOptions: RequestInit & { next?: { revalidate?: number | false } } = {
    method,
    headers,
    signal: controller.signal,
  };

  if (body !== undefined) {
    fetchOptions.body = JSON.stringify(body);
  }

  if (options.cache !== undefined) {
    fetchOptions.cache = options.cache;
  }

  if (options.revalidate !== undefined) {
    fetchOptions.next = { revalidate: options.revalidate };
  }

  try {
    const response = await fetch(fullUrl, fetchOptions);

    if (!response.ok) {
      let detailMsg: string | undefined;
      try {
        const errorData = (await response.json()) as { detail?: string | { msg?: string }[] };
        if (typeof errorData?.detail === "string") {
          detailMsg = errorData.detail;
        } else if (Array.isArray(errorData?.detail)) {
          detailMsg = errorData.detail.map((d) => d.msg ?? JSON.stringify(d)).join(", ");
        }
      } catch {
        // Response body wasn't JSON
      }

      const userMessage =
        detailMsg ?? `Request to ${normalizedPath} failed with status ${response.status} (${response.statusText})`;

      throw new ApiClientError(userMessage, response.status, response.statusText, normalizedPath, detailMsg);
    }

    return (await response.json()) as T;
  } catch (error) {
    if (error instanceof ApiClientError) {
      throw error;
    }

    if (error instanceof Error && error.name === "AbortError") {
      throw new ApiClientError(
        `Request to ${normalizedPath} timed out after ${timeoutMs}ms`,
        408,
        "Request Timeout",
        normalizedPath
      );
    }

    const networkMessage =
      error instanceof Error ? error.message : "Network error occurred while connecting to the API.";
    throw new ApiClientError(
      `Unable to connect to POMPO API at ${fullUrl}: ${networkMessage}`,
      0,
      "Network Error",
      normalizedPath
    );
  } finally {
    clearTimeout(timeoutId);
  }
}

export function apiGet<T>(path: string, options?: RequestOptions): Promise<T> {
  return request<T>(path, "GET", undefined, options);
}

export function apiPost<T, B = unknown>(path: string, body: B, options?: RequestOptions): Promise<T> {
  return request<T>(path, "POST", body, options);
}
