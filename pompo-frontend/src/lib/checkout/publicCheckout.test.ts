import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  catalogMethodPresentation,
  checkoutPhaseFromPayment,
  formatMoney,
  humanizeCustomerError,
  isTerminalPaymentStatus,
  paymentCtaLabel,
  sanitizeAmountInput,
  shouldShowAppInvitation,
  validateStaticAmount,
} from "./publicCheckout.ts";

describe("public checkout helpers", () => {
  it("never treats pending as a terminal failure", () => {
    assert.equal(isTerminalPaymentStatus("processing"), false);
    assert.equal(isTerminalPaymentStatus("pending"), false);
    assert.equal(checkoutPhaseFromPayment("processing"), "pending");
    assert.equal(checkoutPhaseFromPayment("success"), "success");
    assert.equal(checkoutPhaseFromPayment("failed"), "failure");
  });

  it("hides raw backend exceptions from customers", () => {
    assert.equal(
      humanizeCustomerError("Traceback (most recent call last):", "Payment could not be completed."),
      "Payment could not be completed.",
    );
    assert.equal(humanizeCustomerError("QR has expired", "Payment could not be completed."), "QR has expired");
  });

  it("formats MWK amounts without inventing values", () => {
    assert.equal(formatMoney("2500.00"), "MWK 2,500.00");
    assert.equal(formatMoney(null), "MWK —");
  });

  it("classifies catalog methods from backend flags only", () => {
    const sandbox = catalogMethodPresentation({
      available: true,
      is_sandbox: true,
      reason: null,
      authorization_state: "not_required",
    });
    assert.deepEqual(sandbox.badges, ["AVAILABLE", "SANDBOX"]);
    assert.equal(sandbox.selectable, true);

    const tnm = catalogMethodPresentation({
      available: false,
      is_sandbox: false,
      reason: "TNM Mpamba live HTTP contract is not in POMPO. Saved Mpamba is not available.",
      authorization_state: "unsupported",
    });
    assert.equal(tnm.selectable, false);
    assert.ok(tnm.badges.includes("NOT AVAILABLE") || tnm.badges.includes("COMING SOON"));

    const soon = catalogMethodPresentation({
      available: false,
      is_sandbox: false,
      reason: "Coming soon",
      authorization_state: "unsupported",
    });
    assert.deepEqual(soon.badges, ["COMING SOON"]);
  });

  it("shows the app invitation only after success", () => {
    assert.equal(shouldShowAppInvitation("success"), true);
    assert.equal(shouldShowAppInvitation("ready"), false);
    assert.equal(shouldShowAppInvitation("processing"), false);
  });

  it("validates static amounts and sanitizes keypad input", () => {
    assert.equal(validateStaticAmount(""), "Enter the amount you want to pay.");
    assert.equal(validateStaticAmount("1500"), null);
    assert.equal(sanitizeAmountInput("1,500.459"), "1500.45");
  });

  it("keeps the pay CTA explicit", () => {
    assert.equal(
      paymentCtaLabel({ authenticated: true, currency: "MWK", amount: "1500", qrType: "dynamic" }),
      "Pay MWK 1,500.00",
    );
    assert.equal(
      paymentCtaLabel({ authenticated: false, currency: "MWK", amount: null, qrType: "static" }),
      "Continue",
    );
  });
});
