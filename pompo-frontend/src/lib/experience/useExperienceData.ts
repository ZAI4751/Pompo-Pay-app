"use client";

import { useEffect, useState } from "react";
import {
  billCards,
  kpis,
  openingChat,
  railSegments,
  topMerchants,
  volumeSeries,
  walletBalance,
  walletTxns,
  weekdayActivity,
  type BillCard,
  type ChatMessage,
  type Kpi,
  type MerchantRow,
  type VolumePoint,
  type WalletTxn,
} from "./data";

export interface ExperiencePayload {
  balance: number;
  txns: WalletTxn[];
  chat: ChatMessage[];
  bills: BillCard[];
  kpis: Kpi[];
  volume: VolumePoint[];
  weekdays: typeof weekdayActivity;
  rails: typeof railSegments;
  merchants: MerchantRow[];
}

function loadPayload(): ExperiencePayload {
  return {
    balance: walletBalance,
    txns: walletTxns,
    chat: openingChat,
    bills: billCards,
    kpis,
    volume: volumeSeries,
    weekdays: weekdayActivity,
    rails: railSegments,
    merchants: topMerchants,
  };
}

/** Simulated fetch so loading / empty / ready states are real UI paths. */
export function useExperienceData(delayMs = 520) {
  const [data, setData] = useState<ExperiencePayload | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    const timer = window.setTimeout(() => {
      try {
        const payload = loadPayload();
        if (!cancelled) setData(payload);
      } catch {
        if (!cancelled) setError("Could not load demo experience data.");
      }
    }, delayMs);
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
    };
  }, [delayMs]);

  return { data, error, loading: !data && !error };
}
