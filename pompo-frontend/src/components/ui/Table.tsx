"use client";

import { type ReactNode, type TableHTMLAttributes } from "react";
import { m } from "framer-motion";
import { cn } from "@/lib/utils/cn";
import { staggerContainer, staggerItem } from "@/lib/motion";

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-2xl border border-border bg-white dark:border-neutral-800 dark:bg-slate-900/80">
      <table className={cn("w-full min-w-[640px] table-fixed border-collapse text-sm", className)} {...props} />
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-border bg-slate-50 text-left text-[11px] font-semibold uppercase tracking-[0.12em] text-text-subtle dark:bg-slate-900">
      <tr>{children}</tr>
    </thead>
  );
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return (
    <th
      scope="col"
      className={cn("px-4 py-2.5 align-middle font-semibold", className)}
      {...props}
    />
  );
}

export function TableBody({ children }: { children: ReactNode }) {
  return (
    <m.tbody className="bg-white dark:bg-transparent" variants={staggerContainer} initial="hidden" animate="show">
      {children}
    </m.tbody>
  );
}

type TrProps = Omit<
  React.HTMLAttributes<HTMLTableRowElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"
>;

export function Tr({ className, ...props }: TrProps) {
  return (
    <m.tr
      variants={staggerItem}
      className={cn(
        "border-b border-border last:border-0 transition-colors duration-200 hover:bg-primary-light/70",
        "data-[selected=true]:bg-primary-light",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return (
    <td
      className={cn("max-w-[16rem] truncate px-4 py-3 align-middle text-text", className)}
      {...props}
    />
  );
}

export function MonoId({ children }: { children: React.ReactNode }) {
  const title = typeof children === "string" || typeof children === "number" ? String(children) : undefined;
  return (
    <span title={title} className="block max-w-full truncate font-mono text-[12px] tracking-tight text-text-muted">
      {children}
    </span>
  );
}
