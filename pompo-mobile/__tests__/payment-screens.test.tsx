import { fireEvent, render, screen, waitFor } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { catalogMethodSelectable } from "@/domain/paymentMethod";
import PreviewScreen from "../app/customer/preview";
import ConfirmScreen from "../app/customer/confirm";
import ResultScreen from "../app/customer/result";
import type { CheckoutSession } from "@/state/CheckoutProvider";
import type { PaymentMethodCatalogItem, QrInspect } from "@/types";

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

const sandboxMobileMoney: PaymentMethodCatalogItem = {
  provider_code: "simulated",
  instrument_type: "mobile_money",
  label: "POMPO Demo Mobile Money (Sandbox)",
  available: true,
  is_sandbox: true,
  reason: null,
  authorization_state: "not_required",
};

const sandboxVisa: PaymentMethodCatalogItem = {
  ...sandboxMobileMoney,
  instrument_type: "visa",
  label: "Sandbox Visa",
};

const unavailableAirtel: PaymentMethodCatalogItem = {
  provider_code: "airtel_money",
  instrument_type: "mobile_money",
  label: "Airtel Money",
  available: false,
  is_sandbox: false,
  reason: "Coming soon",
  authorization_state: "unsupported",
};

function session(overrides: Partial<CheckoutSession> = {}): CheckoutSession {
  return {
    payload: "POMPO:1:dynamic:QRABC123456789:body:sig",
    publicIdentifier: "QRABC123456789",
    inspect,
    amount: "150.00",
    idempotencyKey: "idemp-1",
    payment: null,
    paymentMethod: sandboxMobileMoney,
    customerPhone: "",
    ...overrides,
  };
}

let mockCheckout: CheckoutSession | null = session();
const mockPaymentMethodCatalog = jest.fn();
const mockSelectPaymentMethod = jest.fn();
const mockSetCustomerPhone = jest.fn();
const mockApi = { paymentMethodCatalog: mockPaymentMethodCatalog };

jest.mock("@/state/CheckoutProvider", () => ({
  useCheckout: () => ({
    session: mockCheckout,
    begin: jest.fn(),
    selectPaymentMethod: mockSelectPaymentMethod,
    setCustomerPhone: mockSetCustomerPhone,
    setPayment: jest.fn(),
    clear: jest.fn(),
  }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    api: mockApi,
  }),
}));

describe("QR and payment screens", () => {
  beforeEach(() => {
    mockCheckout = session();
    mockPaymentMethodCatalog.mockReset();
    mockSelectPaymentMethod.mockReset();
    mockSetCustomerPhone.mockReset();
    mockPaymentMethodCatalog.mockResolvedValue({
      ok: true,
      data: [sandboxMobileMoney, sandboxVisa, unavailableAirtel],
    });
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
    expect(await screen.findByText("POMPO Demo Mobile Money (Sandbox)")).toBeTruthy();
    expect(screen.getAllByText("AVAILABLE · SANDBOX").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText("Sandbox Visa")).toBeTruthy();
    expect(screen.getByText("Airtel Money")).toBeTruthy();
    expect(catalogMethodSelectable(sandboxMobileMoney)).toBe(true);
    expect(catalogMethodSelectable(unavailableAirtel)).toBe(false);
  });

  it("selects a sandbox option from the backend catalog", async () => {
    render(
      <SafeAreaProvider>
        <ConfirmScreen />
      </SafeAreaProvider>,
    );
    const visaOption = await screen.findByRole("button", { name: "Sandbox Visa sandbox" });
    fireEvent.press(visaOption);
    expect(mockSelectPaymentMethod).toHaveBeenCalledWith(sandboxVisa);
  });

  it("shows a retryable error when the backend catalog fails to load", async () => {
    mockPaymentMethodCatalog.mockResolvedValue({
      ok: false,
      error: { message: "Unable to load catalog", requestId: "req-1" },
    });
    render(
      <SafeAreaProvider>
        <ConfirmScreen />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("Retry")).toBeTruthy();
    expect(screen.getByText(/Payment methods could not be loaded/)).toBeTruthy();
    expect(screen.queryByText("No payment methods available")).toBeNull();
    expect(screen.queryByText("Loading payment options…")).toBeNull();
    expect(screen.getByRole("button", { name: "PAY MWK 150.00" })).toBeDisabled();
  });

  it("shows the unavailable state only after a successful catalog load", async () => {
    mockPaymentMethodCatalog.mockResolvedValue({ ok: true, data: [unavailableAirtel] });
    render(
      <SafeAreaProvider>
        <ConfirmScreen />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("No payment methods available")).toBeTruthy();
    expect(screen.queryByText("Retry")).toBeNull();
  });

  it("disables sandbox options rejected by the backend catalog state", async () => {
    const unavailableSandbox = { ...sandboxMobileMoney, authorization_state: "unsupported" };
    mockCheckout = session({ paymentMethod: unavailableSandbox });
    mockPaymentMethodCatalog.mockResolvedValue({ ok: true, data: [unavailableSandbox] });
    render(
      <SafeAreaProvider>
        <ConfirmScreen />
      </SafeAreaProvider>,
    );
    expect(await screen.findByText("POMPO Demo Mobile Money (Sandbox)")).toBeTruthy();
    await waitFor(() => {
      expect(screen.getByRole("button", { name: "PAY MWK 150.00" })).toBeDisabled();
    });
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
