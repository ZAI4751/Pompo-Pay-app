import { extractPublicIdentifier } from "@/domain/qrPayload";

describe("extractPublicIdentifier", () => {
  it("reads a static POMPO payload without verifying the signature", () => {
    const result = extractPublicIdentifier("POMPO:1:static:QRABC123456789:not-a-real-signature-xx");
    expect(result).toEqual({ ok: true, publicIdentifier: "QRABC123456789" });
  });

  it("reads a dynamic payload public id and ignores embedded amount", () => {
    const result = extractPublicIdentifier(
      "POMPO:1:dynamic:QRDYN123456789:15000:MWK:1710000000:PMP-REF:signaturepartxxxxxx",
    );
    expect(result).toEqual({ ok: true, publicIdentifier: "QRDYN123456789" });
  });

  it("accepts a bare public identifier", () => {
    expect(extractPublicIdentifier("QRABC123456789")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
  });

  it("extracts public identifier from canonical HTTPS universal QR URL", () => {
    expect(extractPublicIdentifier("https://pay.pompo.mw/p/QRABC123456789")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
    expect(extractPublicIdentifier("https://pay.pompo.mw/p/QRABC123456789/")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
    expect(extractPublicIdentifier("https://pay.pompo.mw/p/QRABC123456789?ref=scan")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
    expect(extractPublicIdentifier("http://localhost:3000/p/QRABC123456789")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
    expect(extractPublicIdentifier("/p/QRABC123456789")).toEqual({
      ok: true,
      publicIdentifier: "QRABC123456789",
    });
  });

  it("rejects malformed codes", () => {
    expect(extractPublicIdentifier("not-a-pompo-payload").ok).toBe(false);
  });

  it("rejects unsupported versions", () => {
    const result = extractPublicIdentifier("POMPO:99:static:QRABC123456789:signaturepartxxxxxx");
    expect(result).toEqual({ ok: false, message: "Unsupported QR version" });
  });
});
