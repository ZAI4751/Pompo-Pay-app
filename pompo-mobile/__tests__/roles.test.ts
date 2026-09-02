import { canUseMerchantMode, defaultMode } from "@/domain/roles";

describe("mode switching", () => {
  test("customers stay in customer mode", () => {
    expect(defaultMode("customer")).toBe("customer");
    expect(canUseMerchantMode("customer")).toBe(false);
  });

  test("merchant staff default to merchant mode and may switch", () => {
    expect(defaultMode("merchant_owner")).toBe("merchant");
    expect(canUseMerchantMode("cashier")).toBe(true);
  });
});
