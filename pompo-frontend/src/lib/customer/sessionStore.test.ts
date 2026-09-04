import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { parseCheckoutDraftJson, parseCustomerSessionJson } from "./sessionParsers.ts";

describe("customer session persistence parsers", () => {
  it("accepts a token pair and rejects malformed payloads", () => {
    assert.deepEqual(
      parseCustomerSessionJson(JSON.stringify({ accessToken: "a", refreshToken: "r" })),
      { accessToken: "a", refreshToken: "r" },
    );
    assert.equal(parseCustomerSessionJson(JSON.stringify({ accessToken: "a" })), null);
    assert.equal(parseCustomerSessionJson("not-json"), null);
  });

  it("only stores allowlisted checkout return paths", () => {
    assert.deepEqual(parseCheckoutDraftJson(JSON.stringify({ path: "/p/QR123", amount: "1500.00" })), {
      path: "/p/QR123",
      amount: "1500.00",
      methodKey: undefined,
    });
    assert.equal(parseCheckoutDraftJson(JSON.stringify({ path: "https://evil.example" })), null);
    assert.equal(parseCheckoutDraftJson(JSON.stringify({ path: "/account" })), null);
  });
});
