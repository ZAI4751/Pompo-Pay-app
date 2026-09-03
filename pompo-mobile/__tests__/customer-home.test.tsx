import { fireEvent, render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import CustomerHome from "../app/customer/index";

const mockPush = jest.fn();
const mockReplace = jest.fn();

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: mockReplace, push: mockPush, back: jest.fn() }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    user: {
      id: "u1",
      email: "ada@customer.mw",
      full_name: "Ada Phiri",
      merchant_id: null,
      branch_id: null,
      role_id: "r1",
      role_code: "customer",
      is_active: true,
    },
    api: {
      listMyPayments: async () => ({
        ok: true,
        data: [
          {
            id: "p1",
            reference: "PMP-1",
            merchant_id: "m1",
            branch_id: "b1",
            till_id: "t1",
            amount: "150.00",
            currency: "MWK",
            payment_method: "mobile_money",
            status: "success",
            description: null,
            failure_reason: null,
            attempts: [],
            merchant_name: "Chikondi Shop",
            branch_name: "Lilongwe",
            till_name: "Counter 1",
            created_at: "2026-09-03T08:00:00.000Z",
            completed_at: "2026-09-03T08:00:12.000Z",
          },
        ],
      }),
      listMyMerchants: async () => ({ ok: true, data: [] }),
      insights: async () => ({ ok: false, error: { kind: "unavailable", message: "skip" } }),
    },
    logout: jest.fn(),
    login: jest.fn(),
    hydrated: true,
    refreshUser: jest.fn(),
  }),
}));

jest.mock("@/state/ModeProvider", () => ({
  useAppMode: () => ({
    mode: "customer",
    canSwitch: false,
    setMode: jest.fn(),
  }),
}));

describe("Customer home", () => {
  it("shows Scan & pay without wallet or fictional balances", async () => {
    render(
      <SafeAreaProvider>
        <CustomerHome />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("Hello Ada")).toBeTruthy();
    expect(screen.getByText("Scan & pay")).toBeTruthy();
    expect(screen.getByText("OPEN → SCAN → PAY")).toBeTruthy();
    expect(await screen.findByText("Chikondi Shop")).toBeTruthy();
    expect(screen.queryByText(/wallet/i)).toBeNull();
    expect(screen.queryByText(/top up/i)).toBeNull();
    expect(screen.queryByText(/US Dollar/i)).toBeNull();
    expect(screen.queryByText(/total balance/i)).toBeNull();
    fireEvent.press(screen.getByText("Scan & pay"));
    expect(mockPush).toHaveBeenCalledWith("/customer/scan");
  });
});
