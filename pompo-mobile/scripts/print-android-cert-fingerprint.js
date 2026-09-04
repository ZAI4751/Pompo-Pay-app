"use strict";

/**
 * Print the release keystore SHA-256 certificate fingerprint for
 * /.well-known/assetlinks.json. Does not print keystore passwords.
 */

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const keystorePath = path.join(root, "credentials", "release.keystore");
const keystorePropsPath = path.join(root, "credentials", "keystore.properties");

function readProps(filePath) {
  const values = {};
  for (const line of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const match = line.match(/^([^=]+)=(.*)$/);
    if (match) values[match[1].trim()] = match[2];
  }
  return values;
}

if (!fs.existsSync(keystorePath) || !fs.existsSync(keystorePropsPath)) {
  console.error("Release keystore is not present on this machine.");
  console.error("Expected pompo-mobile/credentials/release.keystore (gitignored).");
  process.exit(1);
}

const props = readProps(keystorePropsPath);
const storePassword = props.storePassword;
const alias = props.keyAlias;
if (!storePassword || !alias) {
  console.error("keystore.properties is missing storePassword or keyAlias.");
  process.exit(1);
}

const keytool = process.env.JAVA_HOME
  ? path.join(process.env.JAVA_HOME, "bin", process.platform === "win32" ? "keytool.exe" : "keytool")
  : "keytool";

const result = spawnSync(
  keytool,
  ["-list", "-v", "-keystore", keystorePath, "-alias", alias, "-storepass", storePassword],
  { encoding: "utf8", windowsHide: true },
);

if (result.status !== 0) {
  console.error("keytool failed to read the release certificate.");
  process.exit(result.status ?? 1);
}

const match = (result.stdout || "").match(/SHA256:\s*([0-9A-Fa-f:]+)/);
if (!match) {
  console.error("keytool output did not include a SHA256 fingerprint.");
  process.exit(1);
}

const fingerprint = match[1].trim().toUpperCase();
console.log(`package=mw.pompo.mobile`);
console.log(`sha256_cert_fingerprint=${fingerprint}`);
console.log("Set Vercel env ANDROID_CERT_SHA256_FINGERPRINTS to this value.");
