import { type HTMLAttributes } from "react";
import { cn } from "@/lib/utils/cn";

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  padded?: boolean;
  glow?: boolean;
}

export function Card({ className, padded, glow, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-md border border-border bg-surface card-depth transition-colors duration-150",
        padded && "px-5 py-4",
        glow && "glow-ring",
        className,
      )}
      {...props}
    />
  );
}

export function CardHeader({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      className={cn(
        "flex items-start justify-between gap-3 border-b border-border px-5 py-3.5",
        className,
      )}
      {...props}
    />
  );
}

export function CardBody({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div className={cn("px-5 py-4", className)} {...props} />;
}

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn("text-sm font-semibold tracking-tight text-text", className)} {...props} />;
}

export function CardEyebrow({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return (
    <p
      className={cn(
        "text-[10px] font-semibold uppercase tracking-[0.16em] text-text-subtle",
        className,
      )}
      {...props}
    />
  );
}
