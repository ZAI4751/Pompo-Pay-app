import { initials, roleLabel } from "../src/format";

describe("format helpers", () => {
  it("builds initials from a full name", () => {
    expect(initials("Ada Phiri")).toBe("AP");
    expect(initials("Mercy")).toBe("ME");
  });

  it("labels known POMPO roles", () => {
    expect(roleLabel("merchant_owner")).toBe("Merchant owner");
    expect(roleLabel("customer")).toBe("Customer");
  });
});
