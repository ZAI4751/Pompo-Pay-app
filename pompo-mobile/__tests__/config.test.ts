import {
  isUnsafeReleaseApiUrl,
  PRODUCTION_API_BASE_URL,
  PUBLIC_CHECKOUT_BASE_URL,
  resolveDevApiBaseUrl,
} from "../src/config";

describe("resolveDevApiBaseUrl", () => {
  it("uses the Expo LAN host for physical devices", () => {
    expect(resolveDevApiBaseUrl("192.168.43.92:8081")).toBe("http://192.168.43.92:8000/api/v1");
  });

  it("falls back to localhost for simulators", () => {
    expect(resolveDevApiBaseUrl("localhost:8081")).toBe("http://localhost:8000/api/v1");
    expect(resolveDevApiBaseUrl(null)).toBe("http://localhost:8000/api/v1");
  });
});

describe("isUnsafeReleaseApiUrl", () => {
  it("uses the Render production API and Vercel checkout host", () => {
    expect(PRODUCTION_API_BASE_URL).toBe("https://pompo-pay-app.onrender.com/api/v1");
    expect(PUBLIC_CHECKOUT_BASE_URL).toBe("https://pompo-pay-app.vercel.app");
    expect(isUnsafeReleaseApiUrl(PRODUCTION_API_BASE_URL)).toBe(false);
  });

  it("rejects the retired Railway API in release builds", () => {
    expect(isUnsafeReleaseApiUrl("https://pompo-api-production.up.railway.app/api/v1")).toBe(true);
  });

  it("rejects localhost and cleartext endpoints", () => {
    expect(isUnsafeReleaseApiUrl("http://localhost:8000/api/v1")).toBe(true);
    expect(isUnsafeReleaseApiUrl("http://10.0.2.2:8000/api/v1")).toBe(true);
    expect(isUnsafeReleaseApiUrl("https://127.0.0.1/api/v1")).toBe(true);
  });
});
