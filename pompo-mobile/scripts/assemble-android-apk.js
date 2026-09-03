"use strict";

const { spawnSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..");
const androidDir = path.join(root, "android");
const gradle = process.platform === "win32" ? "gradlew.bat" : "./gradlew";

if (!fs.existsSync(path.join(androidDir, gradle.replace("./", "")))) {
  console.error("Native Android project is missing. Run: npx expo prebuild --platform android");
  process.exit(1);
}

const gradleResult = spawnSync(gradle, ["assembleRelease"], {
  cwd: androidDir,
  stdio: "inherit",
  shell: process.platform === "win32",
  env: process.env,
});

if (gradleResult.status !== 0) {
  process.exit(gradleResult.status ?? 1);
}

const source = path.join(androidDir, "app", "build", "outputs", "apk", "release", "app-release.apk");
if (!fs.existsSync(source)) {
  console.error(`Gradle finished but APK was not found at ${source}`);
  process.exit(1);
}

const destDir = path.join(root, "release");
fs.mkdirSync(destDir, { recursive: true });
const dest = path.join(destDir, "POMPO-1.0.0.apk");
fs.copyFileSync(source, dest);
console.log(`APK written to ${dest}`);
