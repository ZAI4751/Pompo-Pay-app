import { fireEvent, render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import MerchantHome from "../app/merchant/index";

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "owner@shop.mw",
      full_name: "Mercy Banda",
      merchant_id: "m1",
      branch_id: "b1",
      role_id: "r1",
      role_code: "merchant_owner",
      is_active: true,
    },
    api: {
      getMerchant: async () => ({
        ok: true,
        data: {
          id: "m1",
          name: "Chikondi Shop",
          legal_name: null,
          contact_email: "shop@example.com",
          contact_phone: "+265",
          is_active: true,
        },
      }),
    },
    logout: jest.fn(),
    login: jest.fn(),
    hydrated: true,
    refreshUser: jest.fn(),
  }),
}));

jest.mock("@/state/ModeProvider", () => ({
  useAppMode: () => ({
    mode: "merchant",
    canSwitch: true,
    setMode: jest.fn(),
  }),
}));

describe("Merchant mode", () => {
  it("shows operational merchant home rather than an admin dashboard", async () => {
    render(
      <SafeAreaProvider>
        <MerchantHome />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("Chikondi Shop")).toBeTruthy();
    expect(screen.getByText("Show QR")).toBeTruthy();
    fireEvent.press(screen.getByText("Merchant · switch"));
  });
});
