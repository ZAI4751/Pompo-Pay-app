import { resolveDevApiBaseUrl } from "../src/config";

describe("resolveDevApiBaseUrl", () => {
  it("uses the Expo LAN host for physical devices", () => {
    expect(resolveDevApiBaseUrl("192.168.43.92:8081")).toBe("http://192.168.43.92:8000/api/v1");
  });

  it("falls back to localhost for simulators", () => {
    expect(resolveDevApiBaseUrl("localhost:8081")).toBe("http://localhost:8000/api/v1");
    expect(resolveDevApiBaseUrl(null)).toBe("http://localhost:8000/api/v1");
  });
});
