/** Tabular money presentation for MWK amounts stored as decimal strings. */

export function formatMwk(amount: string | number): string {
  const value = typeof amount === "number" ? amount : Number(amount);
  if (!Number.isFinite(value)) return `${amount}`;
  return `MWK ${value.toLocaleString("en-MW", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatCompactCount(value: number): string {
  return value.toLocaleString("en-MW");
}

/** Short MWK labels for dashboard metrics (illustrative series, not ledger math). */
export function formatCompactMwk(value: number): string {
  if (!Number.isFinite(value)) return String(value);
  if (Math.abs(value) >= 1_000_000) {
    return `MWK ${(value / 1_000_000).toLocaleString("en-MW", { maximumFractionDigits: 1 })}M`;
  }
  if (Math.abs(value) >= 10_000) {
    return `MWK ${(value / 1_000).toLocaleString("en-MW", { maximumFractionDigits: 0 })}k`;
  }
  return formatMwk(value);
}
