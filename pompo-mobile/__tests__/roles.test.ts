import { canUseMerchantMode, defaultMode } from "@/domain/roles";

describe("mode switching", () => {
  test("all accounts default to customer mode per customer-first policy", () => {
    expect(defaultMode("customer")).toBe("customer");
    expect(defaultMode("merchant_owner")).toBe("customer");
    expect(defaultMode("cashier")).toBe("customer");
    expect(canUseMerchantMode("customer")).toBe(false);
  });

  test("merchant staff can use merchant mode capability", () => {
    expect(canUseMerchantMode("merchant_owner")).toBe(true);
    expect(canUseMerchantMode("cashier")).toBe(true);
  });
});
