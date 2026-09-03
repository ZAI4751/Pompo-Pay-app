jest.mock("expo-secure-store", () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
  AFTER_FIRST_UNLOCK: "AFTER_FIRST_UNLOCK",
}));

jest.mock("expo-crypto", () => ({
  randomUUID: () => "test-idempotency-key",
}));

jest.mock("expo-camera", () => ({
  CameraView: "CameraView",
  useCameraPermissions: () => [{ granted: true }, jest.fn()],
}));

jest.mock("expo-linear-gradient", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require("react");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { View } = require("react-native");
  return {
    LinearGradient: ({ children, style }: { children: unknown; style?: unknown }) =>
      React.createElement(View, { style }, children),
  };
});

jest.mock("@expo/vector-icons", () => {
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const React = require("react");
  // eslint-disable-next-line @typescript-eslint/no-require-imports
  const { Text } = require("react-native");
  const Icon = ({ name }: { name?: string }) => React.createElement(Text, null, name ?? "icon");
  return { Ionicons: Icon };
});

jest.mock("react-native-qrcode-svg", () => "QRCode");

jest.mock("react-native-safe-area-context", () => ({
  SafeAreaProvider: ({ children }: { children: unknown }) => children,
  SafeAreaView: ({ children }: { children: unknown }) => children,
  useSafeAreaInsets: () => ({ top: 0, right: 0, bottom: 0, left: 0 }),
}));
