const expoPreset = require("jest-expo/jest-preset");

module.exports = {
  ...expoPreset,
  testMatch: ["**/__tests__/**/*.test.ts?(x)"],
  forceExit: true,
  testTimeout: 15000,
  setupFiles: [...(expoPreset.setupFiles ?? []), "<rootDir>/jest.setup.ts"],
  moduleNameMapper: {
    "^react-native/src/setup-env(\\.js)?$": "<rootDir>/jest.rn-setup-env.js",
    "^react-native/setup-env(\\.js)?$": "<rootDir>/jest.rn-setup-env.js",
    "^test-renderer$": "react-test-renderer",
    "^@/(.*)$": "<rootDir>/src/$1",
    ...(expoPreset.moduleNameMapper ?? {}),
  },
};
