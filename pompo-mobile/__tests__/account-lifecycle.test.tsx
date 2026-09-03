import { fireEvent, render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import ReactivateScreen from "../app/reactivate";
import SecurityScreen from "../app/customer/security";

const mockDeactivate = jest.fn();

jest.mock("expo-router", () => ({
  Redirect: () => null,
  useRouter: () => ({ replace: jest.fn(), push: jest.fn() }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    user: { email: "a@b.c", is_email_verified: true, account_status: "active" },
    login: jest.fn(),
    register: jest.fn(),
    logout: jest.fn(),
    hydrated: true,
    api: {
      deactivateAccount: mockDeactivate,
      requestAccountReactivation: jest.fn(),
      reactivateAccount: jest.fn(),
      changePassword: jest.fn(),
      logoutAll: jest.fn(),
      requestEmailVerification: jest.fn(),
      verifyEmail: jest.fn(),
    },
    refreshUser: jest.fn(),
  }),
}));

describe("account lifecycle screens", () => {
  beforeEach(() => {
    mockDeactivate.mockReset();
  });

  it("requires DEACTIVATE confirmation before calling the backend", async () => {
    render(
      <SafeAreaProvider>
        <SecurityScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("ACTIVE")).toBeTruthy();
    fireEvent.changeText(screen.getByPlaceholderText("Type DEACTIVATE to confirm"), "nope");
    fireEvent.press(screen.getByText("Deactivate account"));
    expect(await screen.findByText("Type DEACTIVATE to confirm.")).toBeTruthy();
    expect(mockDeactivate).not.toHaveBeenCalled();
  });

  it("shows the deactivated reactivation state", () => {
    render(
      <SafeAreaProvider>
        <ReactivateScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("Your POMPO account is deactivated.")).toBeTruthy();
    expect(screen.getByText("Request reactivation")).toBeTruthy();
  });
});
