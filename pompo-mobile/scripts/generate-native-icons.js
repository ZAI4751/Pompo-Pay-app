"use strict";

const fs = require("node:fs");
const path = require("node:path");
const { generateImageAsync } = require("@expo/image-utils");

const root = path.resolve(__dirname, "..");
const resDir = path.join(root, "android", "app", "src", "main", "res");

const iconSrc = path.join(root, "assets", "icon.png");
const fgSrc = path.join(root, "assets", "android-icon-foreground.png");
const monoSrc = path.join(root, "assets", "android-icon-monochrome.png");
const splashSrc = path.join(root, "assets", "splash-icon.png");

const DENSITIES = {
  mdpi: { scale: 1, launcher: 48, adaptive: 108, splash: 160 },
  hdpi: { scale: 1.5, launcher: 72, adaptive: 162, splash: 240 },
  xhdpi: { scale: 2, launcher: 96, adaptive: 216, splash: 320 },
  xxhdpi: { scale: 3, launcher: 144, adaptive: 324, splash: 480 },
  xxxhdpi: { scale: 4, launcher: 192, adaptive: 432, splash: 640 },
};

async function generate() {
  console.log("Generating native Android icons and splash assets...");

  for (const [density, dims] of Object.entries(DENSITIES)) {
    const mipmapDir = path.join(resDir, `mipmap-${density}`);
    fs.mkdirSync(mipmapDir, { recursive: true });

    // Clean up any stale/legacy .webp files
    const legacyWebp = [
      "ic_launcher.webp",
      "ic_launcher_round.webp",
      "ic_launcher_foreground.webp",
      "ic_launcher_monochrome.webp",
    ];
    for (const f of legacyWebp) {
      const p = path.join(mipmapDir, f);
      if (fs.existsSync(p)) {
        fs.unlinkSync(p);
      }
    }

    // Generate ic_launcher.png and ic_launcher_round.png
    const launcherResult = await generateImageAsync(
      { projectRoot: root },
      { src: iconSrc, width: dims.launcher, height: dims.launcher, resizeMode: "cover" }
    );
    fs.writeFileSync(path.join(mipmapDir, "ic_launcher.png"), launcherResult.source);
    fs.writeFileSync(path.join(mipmapDir, "ic_launcher_round.png"), launcherResult.source);

    // Generate adaptive foreground
    const fgResult = await generateImageAsync(
      { projectRoot: root },
      { src: fgSrc, width: dims.adaptive, height: dims.adaptive, resizeMode: "cover" }
    );
    fs.writeFileSync(path.join(mipmapDir, "ic_launcher_foreground.png"), fgResult.source);

    // Generate adaptive monochrome
    const monoResult = await generateImageAsync(
      { projectRoot: root },
      { src: monoSrc, width: dims.adaptive, height: dims.adaptive, resizeMode: "cover" }
    );
    fs.writeFileSync(path.join(mipmapDir, "ic_launcher_monochrome.png"), monoResult.source);

    // Generate splashscreen_logo.png in drawable-<density>
    const drawableDir = path.join(resDir, `drawable-${density}`);
    fs.mkdirSync(drawableDir, { recursive: true });
    const splashResult = await generateImageAsync(
      { projectRoot: root },
      { src: splashSrc, width: dims.splash, height: dims.splash, resizeMode: "contain" }
    );
    fs.writeFileSync(path.join(drawableDir, "splashscreen_logo.png"), splashResult.source);

    console.log(
      `✓ Generated assets for ${density} (${dims.launcher}px launcher, ${dims.adaptive}px adaptive, ${dims.splash}px splash)`
    );
  }

  // Ensure mipmap-anydpi-v26/ic_launcher.xml exists and references foreground & monochrome
  const anydpiDir = path.join(resDir, "mipmap-anydpi-v26");
  fs.mkdirSync(anydpiDir, { recursive: true });

  const adaptiveXml = `<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@color/iconBackground"/>
    <foreground android:drawable="@mipmap/ic_launcher_foreground"/>
    <monochrome android:drawable="@mipmap/ic_launcher_monochrome"/>
</adaptive-icon>
`;
  fs.writeFileSync(path.join(anydpiDir, "ic_launcher.xml"), adaptiveXml, "utf8");
  fs.writeFileSync(path.join(anydpiDir, "ic_launcher_round.xml"), adaptiveXml, "utf8");

  console.log("Native Android icons regenerated successfully.");
}

generate().catch((err) => {
  console.error("Error generating native icons:", err);
  process.exit(1);
});
