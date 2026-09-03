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
      getMerchantAccess: async () => ({
        ok: true,
        data: {
          allowed: true,
          merchant: { id: "m1", name: "Chikondi Shop", is_active: true },
          operating_branch_id: "b1",
          operating_till_id: "t1",
          branches: [{ id: "b1", merchant_id: "m1", code: "MAIN", name: "Main Branch", is_active: true }],
          tills: [{ id: "t1", branch_id: "b1", merchant_id: "m1", code: "TILL1", name: "Till 1", is_active: true }],
          can_generate_qr: true,
          permissions: ["qr:create"],
          reason: null,
        },
      }),
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
      listMerchantPayments: async () => ({ ok: true, data: [] }),
      merchantSummary: async () => ({
        ok: true,
        data: {
          merchant_id: "m1",
          payments_today: 0,
          total_today: "0.00",
          successful_all_time: 0,
          currency: "MWK",
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
    expect(await screen.findByText("Waiting for the first scan")).toBeTruthy();
    fireEvent.press(screen.getByText("Merchant · switch"));
  });
});
