/**
 * Replaceable demo content for the public wallet + insights experience.
 * Swap this module for API-backed loaders without rewriting the UI.
 * Never presented as live ledger data — screens render a Demo data badge.
 */

export type WalletTab = "home" | "assistant" | "payment" | "profile";

export interface WalletTxn {
  id: string;
  name: string;
  date: string;
  amount: number;
  kind: "Transfer" | "Transfer In" | "Subscription" | "Payment";
  initials: string;
  tone: "violet" | "orange" | "teal" | "rose" | "slate";
}

export interface ChatMessage {
  id: string;
  role: "assistant" | "user";
  body: string;
  txnId?: string;
}

export interface BillCard {
  id: string;
  title: string;
  masked: string;
  dueLabel: string;
  amount: number;
}

export interface Kpi {
  id: string;
  label: string;
  value: string;
  delta: number;
  icon: "eye" | "users" | "pointer" | "inbox";
}

export interface VolumePoint {
  label: string;
  thisPeriod: number;
  lastPeriod: number;
}

export interface MerchantRow {
  id: string;
  code: string;
  name: string;
  category: string;
  sold: string;
  revenue: number;
  rating: number;
}

export const walletBalance = 15123.45;

export const walletTxns: WalletTxn[] = [
  {
    id: "t1",
    name: "Madelyn Franci",
    date: "22 Sep 2025",
    amount: -100,
    kind: "Transfer",
    initials: "MF",
    tone: "violet",
  },
  {
    id: "t2",
    name: "Mia Park",
    date: "21 Sep 2025",
    amount: 120,
    kind: "Transfer In",
    initials: "MP",
    tone: "teal",
  },
  {
    id: "t3",
    name: "Netflix",
    date: "20 Sep 2025",
    amount: -13.99,
    kind: "Subscription",
    initials: "N",
    tone: "rose",
  },
  {
    id: "t4",
    name: "Amir Khan",
    date: "19 Sep 2025",
    amount: -42.5,
    kind: "Payment",
    initials: "AK",
    tone: "orange",
  },
  {
    id: "t5",
    name: "Chikondi General Store",
    date: "18 Sep 2025",
    amount: -86.0,
    kind: "Payment",
    initials: "CG",
    tone: "slate",
  },
];

export const openingChat: ChatMessage[] = [
  {
    id: "c1",
    role: "assistant",
    body: "Your balance decreased because of a MWK 100.00 payment to Madelyn Franci. Want to see the details?",
  },
  {
    id: "c2",
    role: "user",
    body: "Yes, show me that transfer.",
  },
  {
    id: "c3",
    role: "assistant",
    body: "Here is the transfer. It settled instantly over Airtel Money.",
    txnId: "t1",
  },
];

export const billCards: BillCard[] = [
  {
    id: "b1",
    title: "Phone Bill",
    masked: "xxxx xxxx 2149",
    dueLabel: "Due in 3 days",
    amount: 2050,
  },
  {
    id: "b2",
    title: "Electricity",
    masked: "xxxx xxxx 8831",
    dueLabel: "Due in 11 days",
    amount: 640,
  },
  {
    id: "b3",
    title: "Water",
    masked: "xxxx xxxx 4412",
    dueLabel: "Paid",
    amount: 0,
  },
];

export const incomeTotal = 680;
export const expenseTotal = 1120;

export const kpis: Kpi[] = [
  { id: "k1", label: "Payments", value: "16,431", delta: 15.5, icon: "eye" },
  { id: "k2", label: "Active payers", value: "5,674", delta: 8.2, icon: "users" },
  { id: "k3", label: "QR scans", value: "1,345", delta: -5.0, icon: "pointer" },
  { id: "k4", label: "Settled payouts", value: "46", delta: 12.1, icon: "inbox" },
];

export const volumeSeries: VolumePoint[] = [
  { label: "1 Jan", thisPeriod: 4200, lastPeriod: 3100 },
  { label: "8 Jan", thisPeriod: 6800, lastPeriod: 5200 },
  { label: "15 Jan", thisPeriod: 9100, lastPeriod: 6400 },
  { label: "18 Jan", thisPeriod: 12324, lastPeriod: 5563 },
  { label: "22 Jan", thisPeriod: 10200, lastPeriod: 7800 },
  { label: "29 Jan", thisPeriod: 14100, lastPeriod: 9200 },
];

export const weekdayActivity = [
  { day: "Sun", value: 42 },
  { day: "Mon", value: 61 },
  { day: "Tue", value: 88 },
  { day: "Wed", value: 54 },
  { day: "Thu", value: 47 },
  { day: "Fri", value: 70 },
  { day: "Sat", value: 39 },
];

export const railSegments = [
  { id: "airtel", label: "Airtel Money", value: "2,467", share: 72, tone: "blue" as const },
  { id: "tnm", label: "TNM Mpamba", value: "680", share: 20, tone: "green" as const },
  { id: "bank", label: "Bank rails", value: "267", share: 8, tone: "orange" as const },
];

export const topMerchants: MerchantRow[] = [
  {
    id: "m1",
    code: "#1042",
    name: "Chikondi General Store",
    category: "Retail",
    sold: "2,310 paid",
    revenue: 124839,
    rating: 5.0,
  },
  {
    id: "m2",
    code: "#1098",
    name: "Mzuzu Fresh Market",
    category: "Groceries",
    sold: "1,842 paid",
    revenue: 98640,
    rating: 4.8,
  },
  {
    id: "m3",
    code: "#1114",
    name: "Lilongwe Pharmacy Group",
    category: "Health",
    sold: "964 paid",
    revenue: 54210,
    rating: 4.6,
  },
  {
    id: "m4",
    code: "#1180",
    name: "Area 47 Fuel Stop",
    category: "Energy",
    sold: "721 paid",
    revenue: 41002,
    rating: 4.4,
  },
];

export function formatWallet(amount: number): string {
  const sign = amount < 0 ? "-" : "";
  return `${sign}MWK ${Math.abs(amount).toLocaleString("en-MW", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`;
}

export function formatCompactVolume(amount: number): string {
  if (amount >= 1_000_000) return `MWK ${(amount / 1_000_000).toFixed(1)}M`;
  if (amount >= 1_000) return `MWK ${(amount / 1_000).toFixed(1)}K`;
  return formatWallet(amount);
}
