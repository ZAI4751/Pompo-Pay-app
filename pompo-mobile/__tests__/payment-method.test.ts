import { catalogMethodSelectable, catalogOfferLabel, paymentMethodChargeable, paymentMethodStateLabel } from "@/domain/paymentMethod";
import type { PaymentMethod, PaymentMethodCatalogItem } from "@/types";

const method: PaymentMethod = {
  id: "PIM-1",
  provider_code: "airtel_money",
  provider_display_name: "Airtel Money",
  instrument_type: "mobile_money",
  display_name: "Airtel Money",
  masked_identifier: "+265 88•• ••21",
  status: "active",
  authorization_state: "completed",
  is_default: true,
  is_sandbox: true,
  last_used_at: null,
  created_at: "2026-09-03T00:00:00Z",
};

describe("payment method labels", () => {
  it("marks sandbox available methods without exposing secrets", () => {
    expect(paymentMethodChargeable(method)).toBe(true);
    expect(paymentMethodStateLabel(method)).toBe("AVAILABLE · SANDBOX · DEFAULT");
  });

  it("does not treat revoked methods as chargeable", () => {
    expect(paymentMethodChargeable({ ...method, status: "revoked" })).toBe(false);
    expect(paymentMethodStateLabel({ ...method, status: "revoked", is_default: false })).toBe(
      "REVOKED · SANDBOX",
    );
  });

  it("labels unavailable catalog offers using the backend state", () => {
    const item: PaymentMethodCatalogItem = {
      provider_code: "tnm_mpamba",
      instrument_type: "mobile_money",
      label: "TNM Mpamba",
      available: false,
      is_sandbox: false,
      reason: "Live contract is not ready",
      authorization_state: "unsupported",
    };
    expect(catalogMethodSelectable(item)).toBe(false);
    expect(catalogOfferLabel(item)).toBe("Coming soon");
  });

  it("allows only available catalog methods that need no authorization", () => {
    const sandbox: PaymentMethodCatalogItem = {
      provider_code: "simulated",
      instrument_type: "mobile_money",
      label: "POMPO Demo Mobile Money (Sandbox)",
      available: true,
      is_sandbox: true,
      reason: null,
      authorization_state: "not_required",
    };
    expect(catalogMethodSelectable(sandbox)).toBe(true);
    expect(catalogOfferLabel(sandbox)).toBe("AVAILABLE · SANDBOX");
    expect(catalogMethodSelectable({ ...sandbox, authorization_state: "required" })).toBe(false);
  });
});
