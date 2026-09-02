import { render, screen } from "@testing-library/react-native";

import { AmountDisplay, StatusPill } from "../src/components/glass";

describe("glass primitives", () => {
  it("renders financial amounts and status without wallet copy", () => {
    render(
      <>
        <AmountDisplay value="MWK 150.00" />
        <StatusPill label="Paid" tone="success" />
      </>,
    );
    expect(screen.getByText("MWK 150.00")).toBeTruthy();
    expect(screen.getByText("Paid")).toBeTruthy();
    expect(screen.queryByText(/wallet/i)).toBeNull();
    expect(screen.queryByText(/balance/i)).toBeNull();
  });
});
