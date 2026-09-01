"use client";

import { m } from "framer-motion";

interface RadialMeterProps {
  value: number;
  label: string;
  caption?: string;
}

export function RadialMeter({ value, label, caption }: RadialMeterProps) {
  const pct = Math.min(100, Math.max(0, value));
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (pct / 100) * circumference;

  return (
    <div className="flex items-center gap-3">
      <div className="relative h-[88px] w-[88px] shrink-0">
        <svg viewBox="0 0 88 88" className="h-full w-full -rotate-90" aria-hidden="true">
          <circle
            cx="44"
            cy="44"
            r={radius}
            fill="none"
            className="stroke-border-strong"
            strokeWidth="6"
          />
          <m.circle
            cx="44"
            cy="44"
            r={radius}
            fill="none"
            className="stroke-primary"
            strokeWidth="6"
            strokeLinecap="round"
            strokeDasharray={circumference}
            initial={{ strokeDashoffset: circumference }}
            animate={{ strokeDashoffset: offset }}
            transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
          />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-semibold tabular-nums text-text">
          {pct.toFixed(1)}%
        </span>
      </div>
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-text-subtle">
          {label}
        </p>
        {caption && <p className="mt-1 max-w-[10rem] break-words text-xs text-text-muted">{caption}</p>}
      </div>
    </div>
  );
}
