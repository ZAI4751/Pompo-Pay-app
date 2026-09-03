import { API_BASE_URL } from "@/config";
import type { TokenStore } from "@/auth/secureStorage";
import { messageFromApiPayload } from "@/api/errors";
import type {
  ApiErrorKind,
  ApiResult,
  AppNotification,
  AuthenticatedUser,
  Branch,
  CustomerInsight,
  CustomerPreferences,
  CustomerRegisterResponse,
  FavoriteMerchant,
  GenericSecurityResponse,
  Merchant,
  MerchantAccessResponse,
  MerchantSummary,
  NotificationList,
  Payment,
  PaymentReceipt,
  PaymentRequest,
  PaymentMethod,
  PaymentMethodCatalogItem,
  QrInspect,
  QrRecord,
  SupportTicket,
  Till,
  TokenResponse,
  VerifyEmailResponse,
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

  async register(input: {
    email: string;
    password: string;
    full_name: string;
    phone?: string;
  }): Promise<ApiResult<CustomerRegisterResponse>> {
    const result = await this.request<CustomerRegisterResponse>("/customers/register", {
      method: "POST",
      body: input,
      auth: false,
    });
    if (result.ok) {
      await this.deps.store.setTokens(result.data.access_token, result.data.refresh_token);
    }
    return result;
  }

  async changePassword(currentPassword: string, newPassword: string): Promise<ApiResult<void>> {
    return this.request<void>("/auth/change-password", {
      method: "POST",
      body: { current_password: currentPassword, new_password: newPassword },
      acceptEmpty: true,
    });
  }

  async logoutAll(): Promise<ApiResult<void>> {
    return this.request<void>("/auth/logout-all", { method: "POST", acceptEmpty: true });
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
    payload?: string;
    publicIdentifier?: string;
    idempotencyKey: string;
    amount?: string;
    paymentInstrumentId?: string;
  }): Promise<ApiResult<Payment>> {
    return this.request<Payment>("/payments/from-qr", {
      method: "POST",
      body: {
        ...(input.payload ? { payload: input.payload } : {}),
        ...(input.publicIdentifier && !input.payload
          ? { public_identifier: input.publicIdentifier }
          : {}),
        idempotency_key: input.idempotencyKey,
        ...(input.amount ? { amount: input.amount } : {}),
        ...(input.paymentInstrumentId ? { payment_instrument_id: input.paymentInstrumentId } : {}),
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

  listPaymentMethods(): Promise<ApiResult<PaymentMethod[]>> {
    return this.request<PaymentMethod[]>("/payment-methods");
  }

  paymentMethodCatalog(): Promise<ApiResult<PaymentMethodCatalogItem[]>> {
    return this.request<PaymentMethodCatalogItem[]>("/payment-methods/catalog");
  }

  addPaymentMethod(body: {
    provider_code: string;
    instrument_type: string;
    msisdn?: string;
    card_last4?: string;
    make_default?: boolean;
  }): Promise<ApiResult<PaymentMethod>> {
    return this.request<PaymentMethod>("/payment-methods", { method: "POST", body });
  }

  getPaymentMethod(id: string): Promise<ApiResult<PaymentMethod>> {
    return this.request<PaymentMethod>(`/payment-methods/${encodeURIComponent(id)}`);
  }

  setDefaultPaymentMethod(id: string): Promise<ApiResult<PaymentMethod>> {
    return this.request<PaymentMethod>(`/payment-methods/${encodeURIComponent(id)}/default`, {
      method: "POST",
    });
  }

  revokePaymentMethod(id: string): Promise<ApiResult<PaymentMethod>> {
    return this.request<PaymentMethod>(`/payment-methods/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
  }

  listMyPayments(params?: {
    q?: string;
    status?: string;
    reference?: string;
    merchant_id?: string;
    amount_min?: string;
    amount_max?: string;
    created_from?: string;
    created_to?: string;
  }): Promise<ApiResult<Payment[]>> {
    const query = new URLSearchParams();
    if (params?.q) query.set("q", params.q);
    if (params?.status) query.set("status", params.status);
    if (params?.reference) query.set("reference", params.reference);
    if (params?.merchant_id) query.set("merchant_id", params.merchant_id);
    if (params?.amount_min) query.set("amount_min", params.amount_min);
    if (params?.amount_max) query.set("amount_max", params.amount_max);
    if (params?.created_from) query.set("created_from", params.created_from);
    if (params?.created_to) query.set("created_to", params.created_to);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return this.request<Payment[]>(`/payments/mine${suffix}`);
  }

  listMerchantPayments(params?: {
    q?: string;
    status?: string;
    reference?: string;
  }): Promise<ApiResult<Payment[]>> {
    const query = new URLSearchParams();
    if (params?.q) query.set("q", params.q);
    if (params?.status) query.set("status", params.status);
    if (params?.reference) query.set("reference", params.reference);
    const suffix = query.toString() ? `?${query.toString()}` : "";
    return this.request<Payment[]>(`/payments${suffix}`);
  }

  merchantSummary(): Promise<ApiResult<MerchantSummary>> {
    return this.request<MerchantSummary>("/payments/summary");
  }

  repeatPayment(reference: string, idempotencyKey: string): Promise<ApiResult<Payment>> {
    return this.request<Payment>(`/payments/${encodeURIComponent(reference)}/repeat`, {
      method: "POST",
      body: { idempotency_key: idempotencyKey },
    });
  }

  getReceipt(reference: string): Promise<ApiResult<PaymentReceipt>> {
    return this.request<PaymentReceipt>(`/payments/${encodeURIComponent(reference)}/receipt`);
  }

  listMyMerchants(): Promise<ApiResult<FavoriteMerchant[]>> {
    return this.request<FavoriteMerchant[]>("/customers/me/merchants");
  }

  addFavorite(merchantId: string): Promise<ApiResult<FavoriteMerchant>> {
    return this.request<FavoriteMerchant>("/customers/me/favorites", {
      method: "POST",
      body: { merchant_id: merchantId },
    });
  }

  removeFavorite(merchantId: string): Promise<ApiResult<void>> {
    return this.request<void>(`/customers/me/favorites/${encodeURIComponent(merchantId)}`, {
      method: "DELETE",
      acceptEmpty: true,
    });
  }

  insights(): Promise<ApiResult<CustomerInsight>> {
    return this.request<CustomerInsight>("/customers/me/insights");
  }

  getPreferences(): Promise<ApiResult<CustomerPreferences>> {
    return this.request<CustomerPreferences>("/customers/me/preferences");
  }

  updatePreferences(
    body: Partial<
      Pick<
        CustomerPreferences,
        | "notify_payment_success"
        | "notify_payment_failed"
        | "notify_payment_updates"
        | "notify_payment_requests"
      >
    >,
  ): Promise<ApiResult<CustomerPreferences>> {
    return this.request<CustomerPreferences>("/customers/me/preferences", {
      method: "PATCH",
      body,
    });
  }

  listPaymentRequests(): Promise<ApiResult<PaymentRequest[]>> {
    return this.request<PaymentRequest[]>("/payment-requests");
  }

  inspectPaymentRequest(publicId: string): Promise<ApiResult<PaymentRequest>> {
    return this.request<PaymentRequest>(`/payment-requests/public/${encodeURIComponent(publicId)}`, {
      auth: false,
    });
  }

  createPaymentRequest(body: {
    amount: string;
    description?: string;
    source_payment_reference?: string;
    merchant_id?: string;
    branch_id?: string;
    till_id?: string;
    expires_in_seconds?: number;
    idempotency_key: string;
  }): Promise<ApiResult<PaymentRequest>> {
    return this.request<PaymentRequest>("/payment-requests", { method: "POST", body });
  }

  createBillSplit(body: {
    total_amount: string;
    description?: string;
    source_payment_reference?: string;
    participants: { amount: string; label?: string }[];
    expires_in_seconds?: number;
    idempotency_key: string;
  }): Promise<ApiResult<{ public_identifier: string; requests: PaymentRequest[] }>> {
    return this.request("/payment-requests/splits", { method: "POST", body });
  }

  cancelPaymentRequest(publicId: string): Promise<ApiResult<PaymentRequest>> {
    return this.request<PaymentRequest>(`/payment-requests/${encodeURIComponent(publicId)}/cancel`, {
      method: "POST",
    });
  }

  payPaymentRequest(publicId: string, idempotencyKey: string): Promise<ApiResult<Payment>> {
    return this.request<Payment>(`/payment-requests/${encodeURIComponent(publicId)}/pay`, {
      method: "POST",
      body: { idempotency_key: idempotencyKey },
    });
  }

  listNotifications(): Promise<ApiResult<NotificationList>> {
    return this.request<NotificationList>("/notifications");
  }

  markNotificationRead(id: string): Promise<ApiResult<AppNotification>> {
    return this.request(`/notifications/${encodeURIComponent(id)}/read`, { method: "POST" });
  }

  markAllNotificationsRead(): Promise<ApiResult<NotificationList>> {
    return this.request<NotificationList>("/notifications/read-all", { method: "POST" });
  }

  createSupportRequest(body: {
    category: string;
    subject: string;
    message: string;
    payment_reference?: string;
  }): Promise<ApiResult<SupportTicket>> {
    return this.request<SupportTicket>("/support-requests", { method: "POST", body });
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

  getMerchantAccess(): Promise<ApiResult<MerchantAccessResponse>> {
    return this.request<MerchantAccessResponse>("/organization/my-access");
  }

  requestEmailVerification(email?: string): Promise<ApiResult<GenericSecurityResponse>> {
    return this.request<GenericSecurityResponse>("/auth/verify-email/request", {
      method: "POST",
      body: { email: email ?? null },
    });
  }

  verifyEmail(token: string): Promise<ApiResult<VerifyEmailResponse>> {
    return this.request<VerifyEmailResponse>("/auth/verify-email", {
      method: "POST",
      body: { token },
    });
  }

  forgotPassword(email: string): Promise<ApiResult<GenericSecurityResponse>> {
    return this.request<GenericSecurityResponse>("/auth/forgot-password", {
      method: "POST",
      body: { email },
    });
  }

  resetPassword(token: string, newPassword: string): Promise<ApiResult<GenericSecurityResponse>> {
    return this.request<GenericSecurityResponse>("/auth/reset-password", {
      method: "POST",
      body: { token, new_password: newPassword },
    });
  }

  getSettlementSummary(): Promise<
    ApiResult<{
      currency: string;
      total_settled_amount: string;
      total_fees: string;
      batch_count: number;
      record_count: number;
    }>
  > {
    return this.request("/settlements/summary");
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
      const message = messageFromApiPayload(payload, FALLBACK[kind]);
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
