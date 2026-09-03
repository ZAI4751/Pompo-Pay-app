export function initials(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean);
  if (parts.length === 0) {
    return "P";
  }
  if (parts.length === 1) {
    return parts[0].slice(0, 2).toUpperCase();
  }
  return `${parts[0][0] ?? ""}${parts[parts.length - 1][0] ?? ""}`.toUpperCase();
}

export function roleLabel(roleCode: string): string {
  switch (roleCode) {
    case "customer":
      return "Customer";
    case "merchant_owner":
      return "Merchant owner";
    case "branch_manager":
      return "Branch manager";
    case "cashier":
      return "Cashier";
    case "platform_admin":
      return "Platform admin";
    default:
      return roleCode.replace(/_/g, " ");
  }
}

export function formatWhen(iso: string | null): string {
  if (!iso) {
    return "";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "";
  }
  const now = new Date();
  const time = date.toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  if (date.toDateString() === now.toDateString()) {
    return `Today, ${time}`;
  }
  const yesterday = new Date(now);
  yesterday.setDate(now.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return `Yesterday, ${time}`;
  }
  return date.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

export function groupLabel(iso: string | null): string {
  if (!iso) {
    return "Undated";
  }
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) {
    return "Undated";
  }
  const today = new Date();
  if (date.toDateString() === today.toDateString()) {
    return "Today";
  }
  const yesterday = new Date(today);
  yesterday.setDate(today.getDate() - 1);
  if (date.toDateString() === yesterday.toDateString()) {
    return "Yesterday";
  }
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
}

export function merchantHue(name: string): string {
  const palettes = ["#DBEAFE", "#FEF3C7", "#D1FAE5", "#E0E7FF", "#FCE7F3", "#FFEDD5"];
  let hash = 0;
  for (const char of name) {
    hash = (hash + char.charCodeAt(0)) % palettes.length;
  }
  return palettes[hash] ?? "#DBEAFE";
}
