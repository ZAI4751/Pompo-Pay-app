import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  ACCOUNT_NAV,
  confirmationMatchesDeactivate,
  DEACTIVATION_CONFIRMATION,
  emailDeliveryCopy,
  isCustomerRole,
  isReceiptEligible,
  securityStateCopy,
} from "./customerAccount.ts";

describe("customer account helpers", () => {
  it("requires the exact deactivation phrase", () => {
    assert.equal(DEACTIVATION_CONFIRMATION, "DEACTIVATE");
    assert.equal(confirmationMatchesDeactivate("DEACTIVATE"), true);
    assert.equal(confirmationMatchesDeactivate("deactivate"), false);
    assert.equal(confirmationMatchesDeactivate("yes"), false);
  });

  it("only treats successful payments as receipts", () => {
    assert.equal(isReceiptEligible("success"), true);
    assert.equal(isReceiptEligible("failed"), false);
    assert.equal(isReceiptEligible("pending"), false);
  });

  it("does not invent MFA or email-delivery success", () => {
    const security = securityStateCopy({
      is_active: true,
      is_email_verified: false,
      account_status: "active",
    });
    assert.equal(security.email, "Email not verified");
    assert.equal(security.account, "Account active");
    assert.match(security.mfa, /not available/i);
    assert.match(emailDeliveryCopy("not_configured", "sent"), /not configured/i);
  });

  it("keeps the account nav lightweight", () => {
    assert.deepEqual(
      ACCOUNT_NAV.map((item) => item.section),
      ["profile", "activity", "receipts", "security", "care"],
    );
    assert.equal(isCustomerRole("customer"), true);
    assert.equal(isCustomerRole("platform_admin"), false);
  });
});
