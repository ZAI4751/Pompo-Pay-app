/** Shared response shapes used across every service. */

export interface Paginated<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
}

export interface ApiErrorBody {
  detail: string;
}

/** A single field-level validation problem, as reported by the backend. */
export interface ApiFieldError {
  loc: string[];
  msg: string;
  type: string;
}

/**
 * Why a request failed. "network" means the request never produced an HTTP
 * response (backend down, DNS, blocked by CORS); every other value maps to a
 * real status the server returned. Components branch on this rather than on
 * the message text, so wording can change without breaking behaviour.
 */
export type ApiErrorKind =
  | "network"
  | "unauthorized"
  | "forbidden"
  | "not_found"
  | "conflict"
  | "validation"
  | "rate_limited"
  | "server"
  | "unavailable"
  | "unknown";

export interface ApiError {
  status: "error";
  kind: ApiErrorKind;
  /** Human-readable text safe to show in the UI. */
  message: string;
  /** Absent only when the request never got a response (kind === "network"). */
  httpStatus?: number;
  /** Backend correlation ID, for matching a UI failure to a server log. */
  requestId?: string;
  /** Seconds to wait before retrying, from Retry-After on a 429/503. */
  retryAfterSeconds?: number;
  /** Populated for validation failures (422). */
  fieldErrors?: ApiFieldError[];
}

/** Discriminated result type so components handle every outcome explicitly. */
export type ApiResult<T> = { status: "success"; data: T } | ApiError;
