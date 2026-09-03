import { fireEvent, render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import LoginScreen from "../app/login";

const mockLogin = jest.fn();
const mockPush = jest.fn();

jest.mock("expo-router", () => ({
  Redirect: () => null,
  useRouter: () => ({ replace: jest.fn(), push: mockPush }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    user: null,
    login: mockLogin,
    register: jest.fn(),
    logout: jest.fn(),
    hydrated: true,
    api: {},
    refreshUser: jest.fn(),
  }),
}));

describe("LoginScreen", () => {
  beforeEach(() => {
    mockLogin.mockReset();
    mockPush.mockReset();
    mockLogin.mockResolvedValue({ ok: false, message: "Incorrect email or password" });
  });

  it("submits credentials and shows auth errors", async () => {
    render(
      <SafeAreaProvider>
        <LoginScreen />
      </SafeAreaProvider>,
    );
    expect(screen.getByText("Sign in")).toBeTruthy();
    fireEvent.changeText(screen.getByPlaceholderText("Email"), "a@b.c");
    fireEvent.changeText(screen.getByPlaceholderText("Password"), "nope");
    fireEvent.press(screen.getByText("Continue"));
    expect(mockLogin).toHaveBeenCalledWith("a@b.c", "nope");
    expect(await screen.findByText("Incorrect email or password", {}, { timeout: 2000 })).toBeTruthy();
  });

  it("routes a deactivated account to reactivation", async () => {
    mockLogin.mockResolvedValue({
      ok: false,
      message: "This POMPO account is deactivated.",
      code: "account_deactivated",
    });
    render(
      <SafeAreaProvider>
        <LoginScreen />
      </SafeAreaProvider>,
    );
    fireEvent.changeText(screen.getByPlaceholderText("Email"), "a@b.c");
    fireEvent.changeText(screen.getByPlaceholderText("Password"), "secret");
    fireEvent.press(screen.getByText("Continue"));
    expect(await screen.findByText("Your POMPO account is deactivated.")).toBeTruthy();
    expect(mockPush).toHaveBeenCalledWith("/reactivate");
  });
});
