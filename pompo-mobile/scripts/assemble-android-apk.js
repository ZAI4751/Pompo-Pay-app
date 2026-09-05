"use strict";

/**
 * Local standalone Android release APK.
 *
 * Does not use Expo Go. Bundles JS into a release APK signed with a local
 * upload keystore that is never committed. Passwords stay in
 * credentials/keystore.properties (gitignored) and are loaded by Gradle —
 * they are not written into app/build.gradle.
 */

const { spawnSync } = require("node:child_process");
const crypto = require("node:crypto");
const fs = require("node:fs");
const os = require("node:os");
const path = require("node:path");

const PRODUCTION_API = "https://pompo-api-production.up.railway.app/api/v1";
const PACKAGE_ID = "mw.pompo.mobile";
const VERSION_NAME = "1.0.0";
const root = path.resolve(__dirname, "..");
const androidDir = path.join(root, "android");
const credentialsDir = path.join(root, "credentials");
const keystorePath = path.join(credentialsDir, "release.keystore");
const keystorePropsPath = path.join(credentialsDir, "keystore.properties");
const gradle = process.platform === "win32" ? "gradlew.bat" : "./gradlew";

function resolveToolchainEnv(base) {
  const env = { ...base };
  const defaultJdk = "C:\\Program Files\\Java\\jdk-17";
  const defaultSdk = path.join(os.homedir(), "AppData", "Local", "Android", "Sdk");
  const shortGradleHome = path.join(os.homedir(), ".g");
  fs.mkdirSync(shortGradleHome, { recursive: true });
  env.GRADLE_USER_HOME = shortGradleHome;
  env.CMAKE_VERSION = "3.31.6";
  if (!env.JAVA_HOME && fs.existsSync(defaultJdk)) {
    env.JAVA_HOME = defaultJdk;
  }
  const configuredSdk = env.ANDROID_HOME || env.ANDROID_SDK_ROOT;
  const sdkRoot =
    configuredSdk && fs.existsSync(configuredSdk)
      ? configuredSdk
      : fs.existsSync(defaultSdk)
        ? defaultSdk
        : null;
  if (!sdkRoot) {
    console.error("ANDROID_HOME is not set and the default Android SDK was not found.");
    process.exit(1);
  }
  env.ANDROID_HOME = sdkRoot;
  env.ANDROID_SDK_ROOT = sdkRoot;
  const extras = [env.JAVA_HOME ? path.join(env.JAVA_HOME, "bin") : "", path.join(sdkRoot, "platform-tools")].filter(
    Boolean,
  );
  const existingPath = env.PATH || env.Path || env.path || "";
  const nextPath = `${extras.join(path.delimiter)}${path.delimiter}${existingPath}`;
  env.PATH = nextPath;
  env.Path = nextPath;
  return env;
}

function run(command, args, options = {}) {
  const result = spawnSync(command, args, {
    cwd: options.cwd ?? root,
    stdio: "inherit",
    shell: options.shell ?? false,
    windowsHide: true,
    env: options.env ?? process.env,
  });
  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

function assertSafeApiUrl(url) {
  const normalized = url.trim().replace(/\/$/, "").toLowerCase();
  if (!normalized.startsWith("https://")) {
    console.error("Release APK must use HTTPS.");
    process.exit(1);
  }
  if (
    normalized.includes("localhost") ||
    normalized.includes("127.0.0.1") ||
    normalized.includes("10.0.2.2") ||
    normalized.includes("0.0.0.0")
  ) {
    console.error("Release APK must not target a development API host.");
    process.exit(1);
  }
}

function ensureKeystore(env) {
  fs.mkdirSync(credentialsDir, { recursive: true });
  if (fs.existsSync(keystorePath) && fs.existsSync(keystorePropsPath)) {
    return;
  }
  const password = crypto.randomBytes(24).toString("base64url");
  const keytool = env.JAVA_HOME ? path.join(env.JAVA_HOME, "bin", "keytool") : "keytool";
  const generated = spawnSync(
    keytool,
    [
      "-genkeypair",
      "-v",
      "-storetype",
      "PKCS12",
      "-keystore",
      keystorePath,
      "-alias",
      "pompo-release",
      "-keyalg",
      "RSA",
      "-keysize",
      "2048",
      "-validity",
      "10000",
      "-storepass",
      password,
      "-keypass",
      password,
      "-dname",
      "CN=POMPO, OU=Mobile, O=POMPO, L=Lilongwe, ST=Malawi, C=MW",
    ],
    { stdio: "inherit", windowsHide: true, env },
  );
  if (generated.status !== 0) {
    console.error("Failed to generate the local release keystore.");
    process.exit(generated.status ?? 1);
  }
  const props = [
    `storeFile=${keystorePath.replace(/\\/g, "/")}`,
    `storePassword=${password}`,
    "keyAlias=pompo-release",
    `keyPassword=${password}`,
    "",
  ].join("\n");
  fs.writeFileSync(keystorePropsPath, props, { encoding: "utf8", mode: 0o600 });
}

function injectReleaseSigning() {
  const gradleFile = path.join(androidDir, "app", "build.gradle");
  let source = fs.readFileSync(gradleFile, "utf8");

  if (!source.includes("keystorePropertiesFile")) {
    source = source.replace(
      "android {",
      `def keystorePropertiesFile = rootProject.file("../credentials/keystore.properties")
def keystoreProperties = new Properties()
if (keystorePropertiesFile.exists()) {
    keystoreProperties.load(new FileInputStream(keystorePropertiesFile))
}

android {`,
    );
  }

  const signingBlock = `signingConfigs {
        debug {
            storeFile file('debug.keystore')
            storePassword 'android'
            keyAlias 'androiddebugkey'
            keyPassword 'android'
        }
        release {
            if (keystorePropertiesFile.exists()) {
                storeFile file(keystoreProperties['storeFile'])
                storePassword keystoreProperties['storePassword']
                keyAlias keystoreProperties['keyAlias']
                keyPassword keystoreProperties['keyPassword']
            }
        }
    }`;

  if (!/signingConfigs \{[\s\S]*?\n    \}/.test(source)) {
    console.error("Unexpected app/build.gradle: signingConfigs block missing.");
    process.exit(1);
  }
  source = source.replace(/signingConfigs \{[\s\S]*?\n    \}/, signingBlock);

  source = source.replace(
    `        release {
            // Caution! In production, you need to generate your own keystore file.
            // see https://reactnative.dev/docs/signed-apk-android.
            signingConfig signingConfigs.debug`,
    `        release {
            signingConfig signingConfigs.release`,
  );
  source = source.replace(
    /release \{\s*signingConfig signingConfigs\.debug/,
    `release {
            signingConfig signingConfigs.release`,
  );

  if (!source.includes("signingConfigs.release") || !source.includes("keystorePropertiesFile")) {
    console.error("Failed to inject release signing into app/build.gradle.");
    process.exit(1);
  }
  if (/storePassword "[^"]+"/.test(source) && source.includes("pompo-release")) {
    console.error("Refusing to leave plaintext release keystore passwords in app/build.gradle.");
    process.exit(1);
  }
  fs.writeFileSync(gradleFile, source);
}

function hardenGradleProperties() {
  const file = path.join(androidDir, "gradle.properties");
  let text = fs.readFileSync(file, "utf8");
  text = text.replace(
    /^org\.gradle\.jvmargs=.*$/m,
    "org.gradle.jvmargs=-Xmx4096m -XX:MaxMetaspaceSize=768m",
  );
  text = text.replace(/EX_DEV_CLIENT_NETWORK_INSPECTOR=.*/g, "EX_DEV_CLIENT_NETWORK_INSPECTOR=false");
  text = text.replace(/reactNativeArchitectures=.*/g, "reactNativeArchitectures=armeabi-v7a,arm64-v8a");
  if (!text.includes("android.cmakeVersion")) {
    text += "\nandroid.cmakeVersion=3.31.6\n";
  }
  fs.writeFileSync(file, text);
}

function writeLocalProperties(sdkRoot) {
  const file = path.join(androidDir, "local.properties");
  const cmakeDir = path.join(sdkRoot, "cmake", "3.31.6");
  const lines = [`sdk.dir=${sdkRoot.replace(/\\/g, "/")}`];
  if (fs.existsSync(cmakeDir)) {
    lines.push(`cmake.dir=${cmakeDir.replace(/\\/g, "/")}`);
  }
  lines.push("");
  fs.writeFileSync(file, lines.join("\n"), "utf8");
}

function downloadGradleDistribution() {
  const wrapperProps = path.join(androidDir, "gradle", "wrapper", "gradle-wrapper.properties");
  const text = fs.readFileSync(wrapperProps, "utf8");
  const match = text.match(/distributionUrl=(.+)/);
  if (!match) {
    return;
  }
  const url = match[1].replace(/\\:/g, ":").trim();
  if (!url.startsWith("https://")) {
    return;
  }
  const fileName = path.basename(url);
  const destDir = path.join(process.env.LOCALAPPDATA || os.tmpdir(), "pompo-gradle");
  fs.mkdirSync(destDir, { recursive: true });
  const dest = path.join(destDir, fileName);
  if (!fs.existsSync(dest) || fs.statSync(dest).size < 1_000_000) {
    const curl = process.platform === "win32" ? "curl.exe" : "curl";
    run(curl, [
      "-L",
      "--retry",
      "5",
      "--retry-all-errors",
      "--connect-timeout",
      "30",
      "--max-time",
      "600",
      "-o",
      dest,
      url,
    ]);
  }
  if (!fs.existsSync(dest) || fs.statSync(dest).size < 1_000_000) {
    console.error("Gradle distribution download is missing or too small.");
    process.exit(1);
  }
  const fileUrl = `file\\:///${dest.replace(/\\/g, "/").replace(/ /g, "%20")}`;
  let next = fs.readFileSync(wrapperProps, "utf8");
  next = next.replace(/distributionUrl=.*/, `distributionUrl=${fileUrl}`);
  next = next.replace(/networkTimeout=\d+/, "networkTimeout=300000");
  fs.writeFileSync(wrapperProps, next);
}

function hardenAndroidManifest() {
  const file = path.join(androidDir, "app", "src", "main", "AndroidManifest.xml");
  let text = fs.readFileSync(file, "utf8");
  if (text.includes("android:usesCleartextTraffic=")) {
    text = text.replace(/android:usesCleartextTraffic="true"/g, 'android:usesCleartextTraffic="false"');
  } else {
    text = text.replace("<application ", '<application android:usesCleartextTraffic="false" ');
  }
  if (!text.includes('android:host="pay.pompo.mw"')) {
    const filter = `
      <intent-filter android:autoVerify="true">
        <action android:name="android.intent.action.VIEW"/>
        <category android:name="android.intent.category.DEFAULT"/>
        <category android:name="android.intent.category.BROWSABLE"/>
        <data android:scheme="https" android:host="pay.pompo.mw" android:pathPrefix="/p/"/>
      </intent-filter>`;
    text = text.replace("</activity>", `${filter}\n    </activity>`);
  }
  fs.writeFileSync(file, text);
}

const toolchain = resolveToolchainEnv(process.env);
const apiUrl = (process.env.EXPO_PUBLIC_API_BASE_URL || PRODUCTION_API).replace(/\/$/, "");
assertSafeApiUrl(apiUrl);
ensureKeystore(toolchain);

const prebuildEnv = {
  ...toolchain,
  EXPO_PUBLIC_API_BASE_URL: apiUrl,
  NODE_ENV: "production",
  CI: "1",
  EXPO_NO_TELEMETRY: "1",
};

if (!fs.existsSync(path.join(androidDir, gradle.replace("./", "")))) {
  const expoCli = path.join(root, "node_modules", "expo", "bin", "cli");
  run(process.execPath, [expoCli, "prebuild", "--platform", "android", "--no-install"], { env: prebuildEnv });
}

if (!fs.existsSync(path.join(androidDir, gradle.replace("./", "")))) {
  console.error("Native Android project is missing after prebuild.");
  process.exit(1);
}

injectReleaseSigning();
hardenGradleProperties();
writeLocalProperties(toolchain.ANDROID_HOME);
downloadGradleDistribution();
hardenAndroidManifest();

const gradleEnv = {
  ...toolchain,
  EXPO_PUBLIC_API_BASE_URL: apiUrl,
  NODE_ENV: "production",
  EX_DEV_CLIENT_NETWORK_INSPECTOR: "false",
};

run(gradle, ["assembleRelease", "-PreactNativeArchitectures=armeabi-v7a,arm64-v8a"], {
  cwd: androidDir,
  env: gradleEnv,
  shell: process.platform === "win32",
});

const source = path.join(androidDir, "app", "build", "outputs", "apk", "release", "app-release.apk");
if (!fs.existsSync(source)) {
  console.error(`Gradle finished but APK was not found at ${source}`);
  process.exit(1);
}

const destDir = path.join(root, "release");
fs.mkdirSync(destDir, { recursive: true });
const dest = path.join(destDir, `POMPO-${VERSION_NAME}.apk`);
fs.copyFileSync(source, dest);

const bytes = fs.readFileSync(dest);
const sha256 = crypto.createHash("sha256").update(bytes).digest("hex");
const info = {
  filename: path.basename(dest),
  path: dest,
  package: PACKAGE_ID,
  version: VERSION_NAME,
  versionCode: 1,
  api: apiUrl,
  buildMethod: "expo prebuild --platform android + gradle assembleRelease",
  sha256,
  sizeBytes: bytes.length,
};
fs.writeFileSync(path.join(destDir, "POMPO-1.0.0.json"), `${JSON.stringify(info, null, 2)}\n`);
fs.writeFileSync(path.join(destDir, "POMPO-1.0.0.sha256"), `${sha256}  ${path.basename(dest)}\n`);
console.log(`APK written to ${dest}`);
console.log(`package=${PACKAGE_ID} version=${VERSION_NAME} api=${apiUrl} sha256=${sha256}`);
