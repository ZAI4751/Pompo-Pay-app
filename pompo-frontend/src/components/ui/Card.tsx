"use client";

import { type HTMLAttributes } from "react";
import { m } from "framer-motion";
import { cn } from "@/lib/utils/cn";
import { cardHover, cardTransition } from "@/lib/motion";

interface CardProps extends Omit<HTMLAttributes<HTMLDivElement>, "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"> {
  padded?: boolean;
  glow?: boolean;
  interactive?: boolean;
  glass?: boolean;
}

export function Card({ className, padded, glow, interactive, glass, ...props }: CardProps) {
  return (
    <m.div
      whileHover={interactive ? cardHover : undefined}
      transition={cardTransition}
      className={cn(
        "rounded-md border border-border bg-white card-depth transition-colors duration-200",
        "dark:border-neutral-800 dark:bg-slate-900/80 dark:backdrop-blur-md",
        padded && "px-5 py-4",
        glow && "glow-ring",
        glass && "pompo-glass",
        interactive &&
          "cursor-default hover:shadow-glow dark:hover:shadow-luminous",
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
        "flex items-start justify-between gap-4 border-b border-border px-5 py-3.5",
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
  return (
    <h2 className={cn("truncate text-sm font-semibold tracking-tight text-text", className)} {...props} />
  );
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
