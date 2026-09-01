"use client";

import { m } from "framer-motion";
import { StatusBadge } from "./StatusBadge";
import { MonoId } from "./Table";
import { staggerContainer, staggerItem } from "@/lib/motion";
import type { Transaction } from "@/lib/types/transaction";
import { formatMwk } from "@/lib/format/money";

function formatStamp(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function ActivityTimeline({ items }: { items: Transaction[] }) {
  return (
    <m.ul className="divide-y divide-border" variants={staggerContainer} initial="hidden" animate="show">
      {items.map((txn) => (
        <m.li
          key={txn.id}
          variants={staggerItem}
          className="flex flex-col gap-2 px-5 py-3.5 sm:flex-row sm:items-center sm:justify-between"
        >
          <div className="min-w-0">
            <p className="truncate font-medium text-text">{txn.merchant_name}</p>
            <p className="mt-0.5 truncate text-xs text-text-muted">
              <MonoId>{txn.reference}</MonoId>
              <span className="mx-1.5 text-text-subtle">·</span>
              {txn.provider_name ?? "Unrouted"}
              <span className="mx-1.5 text-text-subtle">·</span>
              {formatStamp(txn.created_at)}
            </p>
          </div>
          <div className="flex shrink-0 items-center gap-3">
            <p className="text-sm font-semibold tabular-nums text-text">{formatMwk(txn.amount)}</p>
            <StatusBadge status={txn.status} />
          </div>
        </m.li>
      ))}
    </m.ul>
  );
}
