import { render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import PreviewScreen from "../app/customer/preview";
import ConfirmScreen from "../app/customer/confirm";
import ResultScreen from "../app/customer/result";
import type { CheckoutSession } from "@/state/CheckoutProvider";
import type { QrInspect } from "@/types";

jest.mock("expo-router", () => ({
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
}));

const inspect: QrInspect = {
  public_identifier: "QRABC123456789",
  qr_type: "dynamic",
  version: 1,
  status: "active",
  merchant_name: "Chikondi Shop",
  branch_name: "Lilongwe",
  till_name: "Counter 1",
  amount: "150.00",
  currency: "MWK",
  payment_reference: "PMP-1",
  expires_at: null,
};

function session(overrides: Partial<CheckoutSession> = {}): CheckoutSession {
  return {
    payload: "POMPO:1:dynamic:QRABC123456789:body:sig",
    publicIdentifier: "QRABC123456789",
    inspect,
    amount: "150.00",
    idempotencyKey: "idemp-1",
    payment: null,
    paymentMethodId: "PIM-TEST",
    ...overrides,
  };
}

let mockCheckout: CheckoutSession | null = session();

jest.mock("@/state/CheckoutProvider", () => ({
  useCheckout: () => ({
    session: mockCheckout,
    begin: jest.fn(),
    selectPaymentMethod: jest.fn(),
    setPayment: jest.fn(),
    clear: jest.fn(),
  }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    api: {
      listPaymentMethods: async () => ({
        ok: true,
        data: [
          {
            id: "PIM-TEST",
            provider_code: "simulated",
            provider_display_name: "Simulated sandbox",
            instrument_type: "mobile_money",
            display_name: "Test Airtel Money",
            masked_identifier: "+265 88•• ••21",
            status: "active",
            authorization_state: "completed",
            is_default: true,
            is_sandbox: true,
            last_used_at: null,
            created_at: "2026-09-03T00:00:00Z",
          },
        ],
      }),
    },
  }),
}));

describe("QR and payment screens", () => {
  beforeEach(() => {
    mockCheckout = session();
  });

  it("shows merchant preview from backend inspect data", () => {
    render(
      <SafeAreaProvider>
        <PreviewScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("Chikondi Shop")).toBeTruthy();
    expect(screen.getByText(/150\.00/)).toBeTruthy();
  });

  it("confirms the server amount before paying", async () => {
    render(
      <SafeAreaProvider>
        <ConfirmScreen />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("How would you like to pay?")).toBeTruthy();
    expect(screen.getAllByText("Chikondi Shop").length).toBeGreaterThan(0);
    expect(await screen.findByText("Test Airtel Money")).toBeTruthy();
  });

  it("renders payment success from backend status", () => {
    mockCheckout = session({
      payment: {
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
        created_at: null,
        completed_at: null,
      },
    });
    render(
      <SafeAreaProvider>
        <ResultScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("Payment successful")).toBeTruthy();
  });

  it("renders payment failure from backend status", () => {
    mockCheckout = session({
      payment: {
        id: "p1",
        reference: "PMP-1",
        merchant_id: "m1",
        branch_id: "b1",
        till_id: "t1",
        amount: "150.00",
        currency: "MWK",
        payment_method: "mobile_money",
        status: "failed",
        description: null,
        failure_reason: "Provider declined",
        attempts: [],
        merchant_name: "Chikondi Shop",
        branch_name: null,
        till_name: null,
        created_at: null,
        completed_at: null,
      },
    });
    render(
      <SafeAreaProvider>
        <ResultScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("Payment did not complete")).toBeTruthy();
    expect(screen.getByText("Provider declined")).toBeTruthy();
  });
});
