import { type ReactNode, type TableHTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

export function Table({ className, ...props }: TableHTMLAttributes<HTMLTableElement>) {
  return (
    <div className="w-full overflow-x-auto rounded-md border border-border bg-surface">
      <table className={cn("w-full border-collapse text-sm", className)} {...props} />
    </div>
  );
}

export function TableHead({ children }: { children: ReactNode }) {
  return (
    <thead className="border-b border-border bg-surface-inset text-left text-[11px] font-semibold uppercase tracking-[0.12em] text-text-subtle">
      <tr>{children}</tr>
    </thead>
  );
}

export function Th({ className, ...props }: React.ThHTMLAttributes<HTMLTableCellElement>) {
  return <th scope="col" className={cn("px-4 py-2.5 font-semibold", className)} {...props} />;
}

export function TableBody({ children }: { children: ReactNode }) {
  return <tbody className="bg-surface">{children}</tbody>;
}

export function Tr({ className, ...props }: React.HTMLAttributes<HTMLTableRowElement>) {
  return (
    <tr
      className={cn(
        "border-b border-border last:border-0 transition-colors duration-100 hover:bg-primary-light/60",
        className,
      )}
      {...props}
    />
  );
}

export function Td({ className, ...props }: React.TdHTMLAttributes<HTMLTableCellElement>) {
  return <td className={cn("px-4 py-3 text-text", className)} {...props} />;
}

export function MonoId({ children }: { children: React.ReactNode }) {
  return (
    <span className="font-mono text-[12px] tracking-tight text-text-muted">{children}</span>
  );
}
