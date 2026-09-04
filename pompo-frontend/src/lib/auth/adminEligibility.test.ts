import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { isDeactivatedLoginMessage, isPlatformAdminRole } from "./adminEligibility.ts";

describe("master admin eligibility helpers", () => {
  it("accepts only platform_admin", () => {
    assert.equal(isPlatformAdminRole("platform_admin"), true);
    assert.equal(isPlatformAdminRole("customer"), false);
    assert.equal(isPlatformAdminRole("merchant_owner"), false);
    assert.equal(isPlatformAdminRole(undefined), false);
  });

  it("detects deactivation without treating admin denial as deactivation", () => {
    assert.equal(isDeactivatedLoginMessage("This POMPO account is deactivated."), true);
    assert.equal(isDeactivatedLoginMessage("This account cannot access Master Admin."), false);
  });
});
