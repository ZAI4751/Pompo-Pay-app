import { fireEvent, render, screen } from "@testing-library/react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import RegisterScreen from "../app/register";

const mockRegister = jest.fn();
const mockReplace = jest.fn();

jest.mock("expo-router", () => ({
  Redirect: () => null,
  useRouter: () => ({ replace: mockReplace, push: jest.fn() }),
}));

jest.mock("@/state/AuthProvider", () => ({
  useAuth: () => ({
    user: null,
    login: jest.fn(),
    register: mockRegister,
    logout: jest.fn(),
    hydrated: true,
    api: {},
    refreshUser: jest.fn(),
  }),
}));

describe("RegisterScreen", () => {
  beforeEach(() => {
    mockRegister.mockReset();
    mockReplace.mockReset();
  });

  it("surfaces backend field-level validation errors", async () => {
    mockRegister.mockResolvedValue({ ok: false, message: "Email address is invalid" });
    render(
      <SafeAreaProvider>
        <RegisterScreen />
      </SafeAreaProvider>,
    );
    fireEvent.changeText(screen.getByPlaceholderText("Full name"), "Chikondi Banda");
    fireEvent.changeText(screen.getByPlaceholderText("Email"), "chikondi@gmail.com");
    fireEvent.changeText(screen.getByPlaceholderText("Password (8+ characters)"), "Password123");
    fireEvent.press(screen.getByText("Create account"));
    expect(mockRegister).toHaveBeenCalledWith({
      email: "chikondi@gmail.com",
      password: "Password123",
      full_name: "Chikondi Banda",
      phone: undefined,
    });
    expect(await screen.findByText("Email address is invalid")).toBeTruthy();
    expect(screen.queryByText("Request validation failed")).toBeNull();
  });
});
