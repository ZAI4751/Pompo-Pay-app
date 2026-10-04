"use client";

import { motion } from "framer-motion";

export default function FlowDiagram({
  steps,
  compact = false,
}: {
  steps: string[];
  compact?: boolean;
}) {
  const displaySteps = compact ? steps.slice(0, 4) : steps;

  return (
    <div className="relative">
      <div
        aria-hidden
        className="absolute left-[15px] top-2 hidden h-[calc(100%-2rem)] w-px bg-slate-line sm:block"
      />
      <ol className="space-y-8">
        {displaySteps.map((stepText, i) => (
          <motion.li
            key={i}
            initial={{ opacity: 0, y: 14 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true, amount: 0.05 }}
            transition={{ duration: 0.5, delay: i * 0.08 }}
            className="relative flex gap-6 pl-0 sm:pl-0"
          >
            <div className="relative z-10 flex h-8 w-8 flex-none items-center justify-center rounded-full bg-brand-gradient text-[13px] font-semibold text-white">
              {i + 1}
            </div>
            <div className="pt-1">
              <p className="max-w-md text-[15px] leading-relaxed text-ink">
                {stepText}
              </p>
            </div>
          </motion.li>
        ))}
      </ol>
    </div>
  );
}
