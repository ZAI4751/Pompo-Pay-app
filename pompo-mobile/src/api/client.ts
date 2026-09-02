import { API_BASE_URL } from "@/config";
import type { TokenStore } from "@/auth/secureStorage";
import type {
  ApiErrorKind,
  ApiResult,
  AuthenticatedUser,
  Branch,
  Merchant,
  Payment,
  QrInspect,
  QrRecord,
  Till,
  TokenResponse,
} from "@/types";

export interface ClientDeps {
  baseUrl: string;
  store: TokenStore;
  fetchImpl?: typeof fetch;
  randomId?: () => string;
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

const FALLBACK: Record<ApiErrorKind, string> = {
  network: "Could not reach POMPO. Check your connection and try again.",
  unauthorized: "Your session expired. Please sign in again.",
  forbidden: "You do not have permission to do that.",
  not_found: "We could not find that.",
  conflict: "That payment or QR is already in use.",
  validation: "Some of those values are not valid.",
  rate_limited: "Too many requests. Wait a moment and try again.",
  server: "POMPO had a problem. Try again shortly.",
  unavailable: "POMPO is temporarily unavailable.",
  unknown: "Something went wrong.",
};

function kindForStatus(status: number): ApiErrorKind {
  return KIND_BY_STATUS[status] ?? (status >= 500 ? "server" : "unknown");
}

function readDetail(payload: unknown): string | undefined {
  if (typeof payload !== "object" || payload === null || !("detail" in payload)) {
    return undefined;
  }
  const detail = (payload as { detail: unknown }).detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail;
  }
  if (Array.isArray(detail) && detail[0] && typeof detail[0] === "object") {
    const first = detail[0] as { msg?: unknown };
    if (typeof first.msg === "string") {
      return first.msg;
    }
  }
  return undefined;
}

function newRequestId(randomId?: () => string): string {
  if (randomId) {
    return randomId();
  }
  return `mbl-${Date.now().toString(16)}-${Math.random().toString(16).slice(2, 10)}`;
}

export class PompoApi {
  private refreshInFlight: Promise<boolean> | null = null;
  private readonly fetchImpl: typeof fetch;

  constructor(private readonly deps: ClientDeps) {
    this.fetchImpl = deps.fetchImpl ?? fetch;
  }

  async login(email: string, password: string): Promise<ApiResult<TokenResponse>> {
    const result = await this.request<TokenResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
      auth: false,
    });
    if (result.ok) {
      await this.deps.store.setTokens(result.data.access_token, result.data.refresh_token);
    }
    return result;
  }

  async logout(): Promise<void> {
    const refresh = await this.deps.store.getRefreshToken();
    if (refresh) {
      await this.request<void>("/auth/logout", {
        method: "POST",
        body: { refresh_token: refresh },
        auth: false,
        acceptEmpty: true,
      });
    }
    await this.deps.store.clear();
  }

  async me(): Promise<ApiResult<AuthenticatedUser>> {
    return this.request<AuthenticatedUser>("/auth/me");
  }

  inspectQr(publicIdentifier: string): Promise<ApiResult<QrInspect>> {
    return this.request<QrInspect>(`/qr/${encodeURIComponent(publicIdentifier)}`, { auth: false });
  }

  payFromQr(input: {
    payload: string;
    idempotencyKey: string;
    amount?: string;
  }): Promise<ApiResult<Payment>> {
    return this.request<Payment>("/payments/from-qr", {
      method: "POST",
      body: {
        payload: input.payload,
        idempotency_key: input.idempotencyKey,
        ...(input.amount ? { amount: input.amount, payment_method: "mobile_money", provider_code: "simulated" } : {}),
      },
    });
  }

  processPayment(reference: string): Promise<ApiResult<Payment>> {
    return this.request<Payment>(`/payments/${encodeURIComponent(reference)}/process`, {
      method: "POST",
    });
  }

  getPayment(reference: string): Promise<ApiResult<Payment>> {
    return this.request<Payment>(`/payments/${encodeURIComponent(reference)}`);
  }

  listMyPayments(): Promise<ApiResult<Payment[]>> {
    return this.request<Payment[]>("/payments/mine");
  }

  listMerchantPayments(): Promise<ApiResult<Payment[]>> {
    return this.request<Payment[]>("/payments");
  }

  createStaticQr(body: { merchant_id: string; branch_id: string; till_id: string }): Promise<ApiResult<QrRecord>> {
    return this.request<QrRecord>("/qr/static", { method: "POST", body });
  }

  createDynamicQr(body: {
    merchant_id: string;
    branch_id: string;
    till_id: string;
    amount: string;
    idempotency_key: string;
  }): Promise<ApiResult<QrRecord>> {
    return this.request<QrRecord>("/qr/dynamic", {
      method: "POST",
      body: {
        ...body,
        currency: "MWK",
        payment_method: "mobile_money",
        provider_code: "simulated",
      },
    });
  }

  listQrs(): Promise<ApiResult<QrRecord[]>> {
    return this.request<QrRecord[]>("/qr");
  }

  revokeQr(publicIdentifier: string): Promise<ApiResult<QrRecord>> {
    return this.request<QrRecord>(`/qr/${encodeURIComponent(publicIdentifier)}/revoke`, {
      method: "POST",
    });
  }

  getMerchant(merchantId: string): Promise<ApiResult<Merchant>> {
    return this.request<Merchant>(`/organization/merchants/${merchantId}`);
  }

  listBranches(merchantId: string): Promise<ApiResult<Branch[]>> {
    return this.request<Branch[]>(`/organization/merchants/${merchantId}/branches`);
  }

  listTills(branchId: string): Promise<ApiResult<Till[]>> {
    return this.request<Till[]>(`/organization/branches/${branchId}/tills`);
  }

  async restoreSession(): Promise<ApiResult<AuthenticatedUser>> {
    const access = await this.deps.store.getAccessToken();
    if (!access) {
      return {
        ok: false,
        error: { kind: "unauthorized", message: FALLBACK.unauthorized },
      };
    }
    const me = await this.me();
    if (me.ok || me.error.kind !== "unauthorized") {
      return me;
    }
    const refreshed = await this.refreshTokens();
    if (!refreshed) {
      await this.deps.store.clear();
      return {
        ok: false,
        error: { kind: "unauthorized", message: FALLBACK.unauthorized },
      };
    }
    return this.me();
  }

  private async refreshTokens(): Promise<boolean> {
    if (this.refreshInFlight) {
      return this.refreshInFlight;
    }
    this.refreshInFlight = this.refreshTokensUnlocked();
    try {
      return await this.refreshInFlight;
    } finally {
      this.refreshInFlight = null;
    }
  }

  private async refreshTokensUnlocked(): Promise<boolean> {
    const refresh = await this.deps.store.getRefreshToken();
    if (!refresh) {
      return false;
    }
    const result = await this.request<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: { refresh_token: refresh },
      auth: false,
      skipRefresh: true,
    });
    if (!result.ok) {
      await this.deps.store.clear();
      return false;
    }
    await this.deps.store.setTokens(result.data.access_token, result.data.refresh_token);
    return true;
  }

  private async request<T>(
    path: string,
    options: {
      method?: "GET" | "POST" | "PATCH" | "DELETE";
      body?: unknown;
      auth?: boolean;
      skipRefresh?: boolean;
      acceptEmpty?: boolean;
    } = {},
  ): Promise<ApiResult<T>> {
    const requestId = newRequestId(this.deps.randomId);
    const headers: Record<string, string> = {
      Accept: "application/json",
      "X-Request-ID": requestId,
    };
    if (options.body !== undefined) {
      headers["Content-Type"] = "application/json";
    }
    if (options.auth !== false) {
      const access = await this.deps.store.getAccessToken();
      if (access) {
        headers.Authorization = `Bearer ${access}`;
      }
    }

    let response: Response;
    try {
      response = await this.fetchImpl(`${this.deps.baseUrl}${path}`, {
        method: options.method ?? "GET",
        headers,
        body: options.body === undefined ? undefined : JSON.stringify(options.body),
      });
    } catch {
      return { ok: false, error: { kind: "network", message: FALLBACK.network, requestId } };
    }

    const responseId = response.headers.get("x-request-id") ?? requestId;

    if (response.status === 401 && options.auth !== false && options.skipRefresh !== true) {
      const refreshed = await this.refreshTokens();
      if (refreshed) {
        return this.request<T>(path, { ...options, skipRefresh: true });
      }
      return {
        ok: false,
        error: { kind: "unauthorized", message: FALLBACK.unauthorized, status: 401, requestId: responseId },
      };
    }

    if (response.status === 204 || options.acceptEmpty) {
      if (response.ok) {
        return { ok: true, data: undefined as T, requestId: responseId };
      }
    }

    let payload: unknown = null;
    const text = await response.text();
    if (text) {
      try {
        payload = JSON.parse(text) as unknown;
      } catch {
        payload = null;
      }
    }

    if (!response.ok) {
      const kind = kindForStatus(response.status);
      const message = readDetail(payload) ?? FALLBACK[kind];
      return {
        ok: false,
        error: { kind, message, status: response.status, requestId: responseId, detail: payload },
      };
    }

    return { ok: true, data: payload as T, requestId: responseId };
  }
}

export function createApiClient(store: TokenStore, fetchImpl?: typeof fetch): PompoApi {
  return new PompoApi({ baseUrl: API_BASE_URL, store, fetchImpl });
}
