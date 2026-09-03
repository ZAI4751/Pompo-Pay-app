import { randomUUID } from "expo-crypto";

import { PompoApi } from "@/api/client";
import type { TokenStore } from "@/auth/secureStorage";
import { extractPublicIdentifier } from "@/domain/qrPayload";
import { mapPaymentStatus } from "@/domain/paymentStatus";

function memoryStore(initial?: { access?: string; refresh?: string }): TokenStore {
  let access = initial?.access ?? null;
  let refresh = initial?.refresh ?? null;
  return {
    async getAccessToken() {
      return access;
    },
    async getRefreshToken() {
      return refresh;
    },
    async setTokens(nextAccess, nextRefresh) {
      access = nextAccess;
      refresh = nextRefresh;
    },
    async clear() {
      access = null;
      refresh = null;
    },
  };
}

function jsonResponse(body: unknown, status = 200, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", "X-Request-ID": "req-test", ...headers },
  });
}

describe("extractPublicIdentifier", () => {
  it("reads a static POMPO payload without verifying the signature", () => {
    const result = extractPublicIdentifier("POMPO:1:static:QRABC123456789:not-a-real-signature");
    expect(result).toEqual({ ok: true, publicIdentifier: "QRABC123456789" });
  });

  it("reads a dynamic payload public id and ignores amount fields", () => {
    const result = extractPublicIdentifier(
      "POMPO:1:dynamic:QRDYN123456789:15000:MWK:9999999999:PMP-1:sigsigsigsigsigsigsigg",
    );
    expect(result).toEqual({ ok: true, publicIdentifier: "QRDYN123456789" });
  });

  it("accepts a bare public identifier", () => {
    expect(extractPublicIdentifier("QRABC123456789")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
  });

  it("rejects malformed payloads", () => {
    expect(extractPublicIdentifier("https://example.com")).toEqual({
      ok: false,
      message: "This is not a POMPO QR code",
    });
  });
});

describe("mapPaymentStatus", () => {
  it("maps backend statuses without inventing new financial states", () => {
    expect(mapPaymentStatus("qr_generated")).toBe("awaiting_confirmation");
    expect(mapPaymentStatus("pending")).toBe("pending");
    expect(mapPaymentStatus("processing")).toBe("processing");
    expect(mapPaymentStatus("success")).toBe("success");
    expect(mapPaymentStatus("failed")).toBe("failed");
    expect(mapPaymentStatus("timeout")).toBe("timeout");
    expect(mapPaymentStatus("mystery")).toBe("unknown");
  });
});

describe("PompoApi", () => {
  it("stores tokens on login and sends them on subsequent calls", async () => {
    const store = memoryStore();
    const fetchImpl = jest.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/login")) {
        return jsonResponse({
          access_token: "access-1",
          refresh_token: "refresh-1",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      if (url.endsWith("/auth/me")) {
        return jsonResponse({
          id: "u1",
          email: "customer@example.com",
          full_name: "Customer",
          merchant_id: null,
          branch_id: null,
          role_id: "r1",
          role_code: "customer",
          is_active: true,
        });
      }
      return jsonResponse({ detail: "missing" }, 404);
    }) as typeof fetch;

    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl, randomId: () => "rid" });
    const login = await api.login("customer@example.com", "secret");
    expect(login.ok).toBe(true);
    const me = await api.me();
    expect(me.ok).toBe(true);
    const meCall = fetchImpl.mock.calls[1];
    const headers = meCall[1]?.headers as Record<string, string>;
    expect(headers.Authorization).toBe("Bearer access-1");
    expect(headers["X-Request-ID"]).toBe("rid");
  });

  it("maps registration 422 field errors instead of the generic detail", async () => {
    const store = memoryStore();
    const fetchImpl = jest.fn(async () => {
      return jsonResponse(
        {
          detail: "Request validation failed",
          request_id: "req-test",
          errors: [{ loc: ["body", "email"], msg: "value is not a valid email address", type: "value_error" }],
        },
        422,
      );
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const result = await api.register({
      email: "not-an-email",
      password: "Password123",
      full_name: "Chikondi Banda",
    });
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.error.kind).toBe("validation");
      expect(result.error.message).toBe("Email address is invalid");
    }
  });

  it("refreshes once on 401 and retries the original request", async () => {
    const store = memoryStore({ access: "expired", refresh: "refresh-1" });
    let meCalls = 0;
    const fetchImpl = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        const body = JSON.parse(String(init?.body));
        expect(body.refresh_token).toBe("refresh-1");
        return jsonResponse({
          access_token: "access-2",
          refresh_token: "refresh-2",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      if (url.endsWith("/auth/me")) {
        meCalls += 1;
        if (meCalls === 1) {
          return jsonResponse({ detail: "expired" }, 401);
        }
        return jsonResponse({
          id: "u1",
          email: "a@b.c",
          full_name: "A",
          merchant_id: null,
          branch_id: null,
          role_id: "r1",
          role_code: "customer",
          is_active: true,
        });
      }
      return jsonResponse({ detail: "no" }, 404);
    }) as typeof fetch;

    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const me = await api.me();
    expect(me.ok).toBe(true);
    expect(await store.getAccessToken()).toBe("access-2");
  });

  it("clears tokens when refresh fails", async () => {
    const store = memoryStore({ access: "expired", refresh: "dead" });
    const fetchImpl = jest.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return jsonResponse({ detail: "Invalid or expired refresh token" }, 401);
      }
      return jsonResponse({ detail: "expired" }, 401);
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const me = await api.me();
    expect(me.ok).toBe(false);
    expect(await store.getAccessToken()).toBeNull();
  });

  it("does not wipe a new login when a stale refresh fails", async () => {
    const store = memoryStore({ access: "expired", refresh: "old-refresh" });
    let finishRefresh: ((value: Response) => void) | undefined;
    const fetchImpl = jest.fn(async (input: RequestInfo | URL) => {
      const url = String(input);
      if (url.endsWith("/auth/me")) {
        return jsonResponse({ detail: "expired" }, 401);
      }
      if (url.endsWith("/auth/refresh")) {
        return await new Promise<Response>((settle) => {
          finishRefresh = settle;
        });
      }
      if (url.endsWith("/auth/login")) {
        return jsonResponse({
          access_token: "access-new",
          refresh_token: "refresh-new",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      if (url.endsWith("/auth/logout")) {
        return new Response(null, { status: 204 });
      }
      return jsonResponse({ detail: "no" }, 404);
    }) as typeof fetch;

    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const staleMe = api.me();
    await new Promise<void>((resolve) => {
      const timer = setInterval(() => {
        if (finishRefresh) {
          clearInterval(timer);
          resolve();
        }
      }, 5);
    });
    await api.logout();
    const login = await api.login("customer@example.com", "secret");
    expect(login.ok).toBe(true);
    expect(await store.getAccessToken()).toBe("access-new");

    finishRefresh?.(jsonResponse({ detail: "Invalid or expired refresh token" }, 401));
    await staleMe;
    expect(await store.getAccessToken()).toBe("access-new");
    expect(await store.getRefreshToken()).toBe("refresh-new");
  });

  it("sends an idempotency key with from-qr", async () => {
    const store = memoryStore({ access: "access-1" });
    const fetchImpl = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      expect(String(input)).toContain("/payments/from-qr");
      const body = JSON.parse(String(init?.body));
      expect(body.idempotency_key).toBe("pay-1");
      expect(body.payload).toContain("POMPO:");
      return jsonResponse({
        id: "p1",
        reference: "PMP-1",
        merchant_id: "m1",
        branch_id: "b1",
        till_id: "t1",
        amount: "10.00",
        currency: "MWK",
        payment_method: "mobile_money",
        status: "pending",
        description: null,
        failure_reason: null,
        attempts: [],
      });
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const result = await api.payFromQr({
      payload: "POMPO:1:static:QRABC123456789:signaturelooks22charsx",
      idempotencyKey: "pay-1",
      amount: "10.00",
    });
    expect(result.ok).toBe(true);
  });

  it("does not send a client amount for dynamic QR payments", async () => {
    const store = memoryStore({ access: "access-1" });
    const fetchImpl = jest.fn(async (_input: RequestInfo | URL, init?: RequestInit) => {
      const body = JSON.parse(String(init?.body));
      expect(body.amount).toBeUndefined();
      return jsonResponse({
        id: "p1",
        reference: "PMP-2",
        merchant_id: "m1",
        branch_id: "b1",
        till_id: "t1",
        amount: "150.00",
        currency: "MWK",
        payment_method: "mobile_money",
        status: "pending",
        description: null,
        failure_reason: null,
        attempts: [],
      });
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    await api.payFromQr({ payload: "POMPO:1:dynamic:QRDYN123456789:x", idempotencyKey: randomUUID() });
    expect(fetchImpl).toHaveBeenCalled();
  });

  it("fetches merchant access capabilities", async () => {
    const store = memoryStore({ access: "access-1" });
    const fetchImpl = jest.fn(async () => {
      return jsonResponse({
        allowed: true,
        merchant: { id: "m1", name: "Shop", is_active: true },
        operating_branch_id: "b1",
        operating_till_id: "t1",
        branches: [],
        tills: [],
        can_generate_qr: true,
        permissions: ["qr:create"],
        reason: null,
      });
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const res = await api.getMerchantAccess();
    expect(res.ok).toBe(true);
    if (res.ok) {
      expect(res.data.allowed).toBe(true);
      expect(res.data.can_generate_qr).toBe(true);
    }
  });

  it("calls email verification and forgot password endpoints", async () => {
    const store = memoryStore();
    const fetchImpl = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/verify-email")) {
        return jsonResponse({ message: "Email verified successfully" });
      }
      if (url.endsWith("/auth/forgot-password")) {
        return jsonResponse({ message: "If the email is registered, instructions have been sent." });
      }
      return jsonResponse({});
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const verifyRes = await api.verifyEmail("token-123");
    expect(verifyRes.ok).toBe(true);
    const forgotRes = await api.forgotPassword("user@example.com");
    expect(forgotRes.ok).toBe(true);
  });

  it("calls deactivate and reactivate account endpoints", async () => {
    const store = memoryStore({ access: "access-1" });
    const fetchImpl = jest.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
      const url = String(input);
      if (url.endsWith("/auth/deactivate-account")) {
        expect(init?.method).toBe("POST");
        const body = JSON.parse(String(init?.body));
        expect(body.confirmation).toBe("DEACTIVATE");
        return new Response(null, { status: 204 });
      }
      if (url.endsWith("/auth/reactivate-account/request")) {
        return jsonResponse({
          detail: "If a deactivated account matches that email, reactivation instructions have been sent.",
        });
      }
      if (url.endsWith("/auth/reactivate-account")) {
        return jsonResponse({
          access_token: "new-access",
          refresh_token: "new-refresh",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      return jsonResponse({});
    }) as typeof fetch;
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const deactivated = await api.deactivateAccount("secret", "DEACTIVATE");
    expect(deactivated.ok).toBe(true);
    const requested = await api.requestAccountReactivation("user@example.com");
    expect(requested.ok).toBe(true);
    const reactivated = await api.reactivateAccount("token-1", "secret");
    expect(reactivated.ok).toBe(true);
    expect(await store.getAccessToken()).toBe("new-access");
  });
});
