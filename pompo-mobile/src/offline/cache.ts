let historyCache: import("@/types").Payment[] = [];
let offline = false;

export function rememberPayments(rows: import("@/types").Payment[]): void {
  historyCache = rows;
  offline = false;
}

export function cachedPayments(): import("@/types").Payment[] {
  return historyCache;
}

export function markOffline(): void {
  offline = true;
}

export function isOffline(): boolean {
  return offline;
}

export function markOnline(): void {
  offline = false;
}
