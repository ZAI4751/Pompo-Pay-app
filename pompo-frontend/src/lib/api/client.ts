/**
 * Thin fetch wrapper for the ONE real backend integration in this app:
 * authentication (see src/lib/api/services/auth.ts). Every other service
 * currently reads from src/mocks -- see docs/admin-ui-architecture.md.
 *
 * Deliberately does not implement automatic refresh-on-401 retry here;
 * that logic lives in AuthContext (src/lib/auth/AuthContext.tsx) where the
 * session state actually lives, so there is exactly one place that decides
 * "the session is over, redirect to /login" instead of two.
 */

import { API_BASE_URL } from "./config";
import type {
  ApiError,
  ApiErrorKind,
  ApiFieldError,
  ApiResult,
} from "@/lib/types/common";

interface RequestOptions {
  method?: "GET" | "POST" | "PATCH" | "DELETE";
  body?: unknown;
  accessToken?: string;
}

const KIND_BY_STATUS: Record<number, ApiErrorKind> = {
  401: "unauthorized",
  403: "forbidden",
  404: "not_found",
  409: "conflict",
  422: "validation",
  429: "rate_limited",
  503: "unavailable",
};

/**
 * Fallback wording used only when the backend sends no usable `detail`.
 * A server-supplied detail always wins, so endpoint-specific messages
 * (for example "Incorrect email or password") reach the user unchanged.
 */
const FALLBACK_MESSAGE: Record<ApiErrorKind, string> = {
  network: "Could not reach the Pompo backend. Check that the API is running.",
  unauthorized: "Your session has expired. Please sign in again.",
  forbidden: "You do not have permission to perform this action.",
  not_found: "The requested resource was not found.",
  conflict: "That change conflicts with the current state of the resource.",
  validation: "Some of the submitted values are invalid.",
  rate_limited: "Too many requests. Please wait and try again.",
  server: "The server encountered an error. Please try again.",
  unavailable: "The service is temporarily unavailable. Please try again shortly.",
  unknown: "The request failed unexpectedly.",
};

function kindForStatus(status: number): ApiErrorKind {
  const mapped = KIND_BY_STATUS[status];
  if (mapped) return mapped;
  if (status >= 500) return "server";
  return "unknown";
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** Pull field errors out of either the Pompo shape or FastAPI's default. */
function readFieldErrors(payload: unknown): ApiFieldError[] | undefined {
  if (!isRecord(payload)) return undefined;
  const raw = Array.isArray(payload.errors)
    ? payload.errors
    : Array.isArray(payload.detail)
      ? payload.detail
      : undefined;
  if (!raw) return undefined;

  const parsed = raw.filter(isRecord).map((entry) => ({
    loc: Array.isArray(entry.loc) ? entry.loc.map(String) : [],
    msg: String(entry.msg ?? ""),
    type: String(entry.type ?? ""),
  }));
  return parsed.length > 0 ? parsed : undefined;
}

/**
 * Extract a displayable message. `detail` is a plain string on Pompo's own
 * error responses, but FastAPI's default validation shape makes it an array
 * of objects -- stringifying that yields "[object Object]", so it is
 * summarised from the field errors instead.
 */
function readMessage(
  payload: unknown,
  kind: ApiErrorKind,
  fieldErrors: ApiFieldError[] | undefined,
): string {
  if (isRecord(payload) && typeof payload.detail === "string" && payload.detail.trim()) {
    return payload.detail;
  }
  if (fieldErrors?.length) {
    return fieldErrors
      .map((error) => {
        // Drop the leading "body"/"query" segment; it means nothing to a user.
        const field = error.loc.slice(1).join(".") || error.loc.join(".");
        return field ? `${field}: ${error.msg}` : error.msg;
      })
      .join("; ");
  }
  return FALLBACK_MESSAGE[kind];
}

function readRetryAfter(response: Response): number | undefined {
  const header = response.headers.get("Retry-After");
  if (!header) return undefined;
  const seconds = Number.parseInt(header, 10);
  return Number.isFinite(seconds) ? seconds : undefined;
}

function readRequestId(response: Response, payload: unknown): string | undefined {
  const header = response.headers.get("X-Request-ID");
  if (header) return header;
  if (isRecord(payload) && typeof payload.request_id === "string") {
    return payload.request_id;
  }
  return undefined;
}

/** Parse a body as JSON, falling back to raw text for non-JSON error pages. */
async function readPayload(response: Response): Promise<unknown> {
  const text = await response.text().catch(() => "");
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    // Middleware rejections (for example a trusted-host 400) answer in plain
    // text; surfacing it beats discarding the only diagnostic available.
    return { detail: text.slice(0, 300) };
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestOptions = {},
): Promise<ApiResult<T>> {
  const { method = "GET", body, accessToken } = options;

  let response: Response;
  try {
    response = await fetch(`${API_BASE_URL}${path}`, {
      method,
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
      },
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch (cause) {
    // fetch() only rejects when no HTTP response was obtained at all: the
    // backend is down, DNS/TLS failed, or the browser blocked the response
    // because it carried no CORS headers. Anything that DID produce a status
    // is handled below, so a real 4xx/5xx is never mislabelled as unreachable.
    if (process.env.NODE_ENV !== "production") {
      console.error(`[api] ${method} ${API_BASE_URL}${path} did not complete`, cause);
    }
    return { status: "error", kind: "network", message: FALLBACK_MESSAGE.network };
  }

  if (response.status === 204) {
    return { status: "success", data: undefined as T };
  }

  const payload = await readPayload(response);

  if (!response.ok) {
    const kind = kindForStatus(response.status);
    const fieldErrors = kind === "validation" ? readFieldErrors(payload) : undefined;
    const error: ApiError = {
      status: "error",
      kind,
      message: readMessage(payload, kind, fieldErrors),
      httpStatus: response.status,
    };

    const requestId = readRequestId(response, payload);
    if (requestId) error.requestId = requestId;

    const retryAfterSeconds = readRetryAfter(response);
    if (retryAfterSeconds !== undefined) error.retryAfterSeconds = retryAfterSeconds;

    if (fieldErrors) error.fieldErrors = fieldErrors;

    return error;
  }

  return { status: "success", data: payload as T };
}
