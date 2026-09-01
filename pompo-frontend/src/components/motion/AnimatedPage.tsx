"use client";

import { m } from "framer-motion";
import type { ReactNode } from "react";
import { fadeScale } from "@/lib/motion";

export function AnimatedPage({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <m.div
      className={className}
      variants={fadeScale}
      initial="hidden"
      animate="show"
    >
      {children}
    </m.div>
  );
}
