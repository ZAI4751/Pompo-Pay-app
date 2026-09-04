import { NextResponse } from "next/server";

const PACKAGE_NAME = "mw.pompo.mobile";

/**
 * Android App Links for https://pay.pompo.mw/p/...
 *
 * Fingerprints are public certificate material, not secrets. They must be the
 * real release signing cert SHA-256 values (colon-separated hex). Do not invent
 * them. Set ANDROID_CERT_SHA256_FINGERPRINTS on Vercel (comma-separated if
 * upload keystore and Play App Signing both exist).
 */
export const dynamic = "force-dynamic";

function fingerprints(): string[] {
  return (process.env.ANDROID_CERT_SHA256_FINGERPRINTS ?? "")
    .split(",")
    .map((value) => value.trim().toUpperCase())
    .filter((value) => /^[0-9A-F]{2}(:[0-9A-F]{2}){31}$/.test(value));
}

export function GET() {
  const sha256CertFingerprints = fingerprints();
  if (sha256CertFingerprints.length === 0) {
    return NextResponse.json(
      { detail: "android_app_links_not_configured" },
      { status: 404 },
    );
  }
  return NextResponse.json(
    [
      {
        relation: ["delegate_permission/common.handle_all_urls"],
        target: {
          namespace: "android_app",
          package_name: PACKAGE_NAME,
          sha256_cert_fingerprints: sha256CertFingerprints,
        },
      },
    ],
    {
      headers: {
        "Cache-Control": "public, max-age=300",
      },
    },
  );
}
