import { isUnsafeReleaseApiUrl, resolveDevApiBaseUrl } from "../src/config";

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
  it("accepts the production Railway HTTPS API", () => {
    expect(isUnsafeReleaseApiUrl("https://pompo-api-production.up.railway.app/api/v1")).toBe(false);
  });

  it("rejects localhost and cleartext endpoints", () => {
    expect(isUnsafeReleaseApiUrl("http://localhost:8000/api/v1")).toBe(true);
    expect(isUnsafeReleaseApiUrl("http://10.0.2.2:8000/api/v1")).toBe(true);
    expect(isUnsafeReleaseApiUrl("https://127.0.0.1/api/v1")).toBe(true);
  });
});
