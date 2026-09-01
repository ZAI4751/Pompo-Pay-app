"use client";

import { m } from "framer-motion";
import type { ReactNode } from "react";
import { staggerContainer, staggerItem } from "@/lib/motion";
import { cn } from "@/lib/utils/cn";

export function Stagger({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <m.div className={className} variants={staggerContainer} initial="hidden" animate="show">
      {children}
    </m.div>
  );
}

export function StaggerItem({
  children,
  className,
}: {
  children: ReactNode;
  className?: string;
}) {
  return (
    <m.div className={cn("min-w-0", className)} variants={staggerItem}>
      {children}
    </m.div>
  );
}
