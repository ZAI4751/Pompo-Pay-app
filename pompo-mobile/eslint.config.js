const expoConfig = require("eslint-config-expo/flat");
const { defineConfig } = require("eslint/config");

module.exports = defineConfig([
  ...expoConfig,
  {
    ignores: ["dist/*", "node_modules/*", ".expo/*", "coverage/*", "scripts/*"],
  },
  {
    rules: {
      "react-hooks/set-state-in-effect": "off",
      "react-hooks/preserve-manual-memoization": "off",
    },
  },
]);
