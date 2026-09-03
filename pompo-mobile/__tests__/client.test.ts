import { PompoApi } from "@/api/client";
import type { TokenStore } from "@/auth/secureStorage";
import { canUseMerchantMode, defaultMode } from "@/domain/roles";

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

function jsonResponse(status: number, body: unknown, headers: Record<string, string> = {}): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("PompoApi", () => {
  it("refreshes once on 401 and retries the original call", async () => {
    const store = memoryStore({ access: "expired", refresh: "refresh-1" });
    const calls: string[] = [];
    const fetchImpl: typeof fetch = async (input, init) => {
      const url = String(input);
      calls.push(`${init?.method ?? "GET"} ${url}`);
      if (url.endsWith("/auth/refresh")) {
        return jsonResponse(200, {
          access_token: "new-access",
          refresh_token: "new-refresh",
          token_type: "bearer",
          expires_in: 900,
        });
      }
      const auth = (init?.headers as Record<string, string>).Authorization;
      if (auth === "Bearer expired") {
        return jsonResponse(401, { detail: "expired" });
      }
      return jsonResponse(200, { id: "u1", email: "a@b.c", full_name: "A", merchant_id: null, branch_id: null, role_id: "r", role_code: "customer", is_active: true });
    };
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const me = await api.me();
    expect(me.ok).toBe(true);
    expect(await store.getAccessToken()).toBe("new-access");
    expect(calls.filter((call) => call.includes("/auth/me")).length).toBe(2);
  });

  it("sends the same idempotency key for payment initiation", async () => {
    const store = memoryStore({ access: "tok" });
    let body: Record<string, unknown> | null = null;
    const fetchImpl: typeof fetch = async (_input, init) => {
      body = JSON.parse(String(init?.body));
      return jsonResponse(201, { reference: "PMP-1", status: "pending", amount: "10.00" });
    };
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    await api.payFromQr({ payload: "POMPO:1:static:QRABC123456789:sig", idempotencyKey: "abc-123" });
    expect(body).toMatchObject({
      payload: "POMPO:1:static:QRABC123456789:sig",
      idempotency_key: "abc-123",
    });
  });

  it("does not send amount for dynamic QR initiation", async () => {
    const store = memoryStore({ access: "tok" });
    let body: Record<string, unknown> | null = null;
    const fetchImpl: typeof fetch = async (_input, init) => {
      body = JSON.parse(String(init?.body));
      return jsonResponse(201, { reference: "PMP-1", status: "pending" });
    };
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    await api.payFromQr({ payload: "POMPO:1:dynamic:QRDYN123456789:x", idempotencyKey: "dyn-1" });
    expect(body).toEqual({ payload: "POMPO:1:dynamic:QRDYN123456789:x", idempotency_key: "dyn-1" });
  });

  it("clears tokens when refresh fails", async () => {
    const store = memoryStore({ access: "expired", refresh: "dead" });
    const fetchImpl: typeof fetch = async (input) => {
      const url = String(input);
      if (url.endsWith("/auth/refresh")) {
        return jsonResponse(401, { detail: "Invalid or expired refresh token" });
      }
      return jsonResponse(401, { detail: "expired" });
    };
    const api = new PompoApi({ baseUrl: "https://api.test/api/v1", store, fetchImpl });
    const me = await api.me();
    expect(me.ok).toBe(false);
    expect(await store.getAccessToken()).toBeNull();
  });
});

describe("mode switching", () => {
  it("keeps customers in customer mode and defaults all to customer mode", () => {
    expect(canUseMerchantMode("customer")).toBe(false);
    expect(defaultMode("customer")).toBe("customer");
    expect(defaultMode("merchant_owner")).toBe("customer");
  });
});
