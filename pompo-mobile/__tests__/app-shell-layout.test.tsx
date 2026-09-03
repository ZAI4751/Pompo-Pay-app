import { render, screen } from "@testing-library/react-native";
import { Text } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AppShell } from "@/components/AppShell";

const mockPathname = jest.fn(() => "/customer");

jest.mock("expo-router", () => ({
  usePathname: () => mockPathname(),
  useRouter: () => ({ replace: jest.fn(), push: jest.fn(), back: jest.fn() }),
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
  }),
}));

jest.mock("@/state/ModeProvider", () => ({
  useAppMode: () => ({
    mode: "customer",
    canSwitch: false,
    setMode: jest.fn(),
  }),
}));

describe("AppShell", () => {
  beforeEach(() => {
    mockPathname.mockReturnValue("/customer");
  });

  it("keeps the bottom nav mounted in the shell rather than inside page content", () => {
    render(
      <SafeAreaProvider>
        <AppShell>
          <Text>Page body</Text>
        </AppShell>
      </SafeAreaProvider>,
    );
    expect(screen.getByTestId("pompo-app-shell")).toBeTruthy();
    expect(screen.getByTestId("pompo-app-shell-content")).toBeTruthy();
    expect(screen.getByTestId("pompo-persistent-bottom-nav")).toBeTruthy();
    expect(screen.getByText("Page body")).toBeTruthy();
    expect(screen.getByText("Home")).toBeTruthy();
    expect(screen.getByText("Profile")).toBeTruthy();
    const shell = screen.getByTestId("pompo-app-shell");
    const nav = screen.getByTestId("pompo-persistent-bottom-nav");
    expect(JSON.stringify(shell.props.style)).toContain('"backgroundColor":"#f8fafc"');
    expect(JSON.stringify(nav.props.style)).toContain('"backgroundColor":"#f8fafc"');
    expect(JSON.stringify(shell.props.style)).not.toContain('"backgroundColor":"#ffffff"');
  });
});
