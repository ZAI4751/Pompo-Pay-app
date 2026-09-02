"use client";

import { useMemo, useState } from "react";
import { ArrowUpRight } from "lucide-react";
import type { VolumePoint } from "@/lib/experience/data";
import { formatCompactVolume } from "@/lib/experience/data";

export function VolumeChart({ data }: { data: VolumePoint[] }) {
  const [hover, setHover] = useState<number | null>(null);
  const width = 640;
  const height = 220;
  const pad = 28;
  const max = Math.max(...data.flatMap((point) => [point.thisPeriod, point.lastPeriod]), 1);

  const coords = useMemo(
    () =>
      data.map((point, index) => {
        const x = pad + (index / Math.max(data.length - 1, 1)) * (width - pad * 2);
        const yThis = height - pad - (point.thisPeriod / max) * (height - pad * 2);
        const yLast = height - pad - (point.lastPeriod / max) * (height - pad * 2);
        return { ...point, x, yThis, yLast };
      }),
    [data, max],
  );

  if (data.length === 0) {
    return (
      <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
        <p className="text-sm font-semibold text-text">Total volume</p>
        <div className="mt-4 h-[220px] animate-pulse rounded-2xl bg-surface-inset" />
      </article>
    );
  }

  const line = (key: "yThis" | "yLast") =>
    coords.map((point, index) => `${index === 0 ? "M" : "L"}${point.x.toFixed(1)} ${point[key].toFixed(1)}`).join(" ");

  const first = coords[0];
  const last = coords[coords.length - 1];
  const area =
    first && last
      ? `${line("yThis")} L${last.x} ${height - pad} L${first.x} ${height - pad} Z`
      : "";
  const active = hover === null ? null : coords[hover];
  const total = data.reduce((sum, point) => sum + point.thisPeriod, 0);

  return (
    <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <p className="text-sm font-semibold text-text">Total volume</p>
          <p className="mt-1 text-3xl font-semibold tabular-nums text-text">{formatCompactVolume(total)}</p>
          <p className="mt-1 inline-flex items-center gap-1 text-sm font-semibold text-emerald-600">
            <ArrowUpRight className="h-4 w-4" />
            24.4% vs. last period
          </p>
        </div>
        <div className="flex gap-4 text-xs text-text-muted">
          <span className="flex items-center gap-1.5">
            <span className="h-0.5 w-4 bg-primary" /> This period
          </span>
          <span className="flex items-center gap-1.5">
            <span className="h-px w-4 border-t border-dashed border-text-subtle" /> Last period
          </span>
        </div>
      </div>
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="mt-4 h-[220px] w-full"
        role="img"
        aria-label="Payment volume this period versus last period"
        onMouseLeave={() => setHover(null)}
      >
        <defs>
          <linearGradient id="volume-fill" x1="0" x2="0" y1="0" y2="1">
            <stop offset="0%" stopColor="#2563eb" stopOpacity="0.28" />
            <stop offset="100%" stopColor="#2563eb" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        <path d={area} fill="url(#volume-fill)" />
        <path d={line("yLast")} fill="none" stroke="#94a3b8" strokeDasharray="5 5" strokeWidth="2" />
        <path d={line("yThis")} fill="none" stroke="#2563eb" strokeWidth="2.5" strokeLinejoin="round" />
        {coords.map((point, index) => (
          <g key={point.label}>
            <rect
              x={point.x - 24}
              y={0}
              width="48"
              height={height}
              fill="transparent"
              onMouseEnter={() => setHover(index)}
            />
            <text x={point.x} y={height - 8} textAnchor="middle" className="fill-text-subtle" fontSize="11">
              {point.label}
            </text>
          </g>
        ))}
        {active ? (
          <g>
            <line x1={active.x} x2={active.x} y1={pad} y2={height - pad} stroke="#94a3b8" strokeDasharray="3 3" />
            <circle cx={active.x} cy={active.yThis} r="5" fill="#2563eb" />
            <foreignObject x={Math.min(active.x + 8, width - 170)} y={18} width="160" height="72">
              <div className="rounded-2xl bg-white px-3 py-2 text-xs shadow-lg dark:bg-slate-800">
                <p className="font-semibold text-text">{active.label}</p>
                <p className="text-primary">This {formatCompactVolume(active.thisPeriod)}</p>
                <p className="text-text-subtle">Last {formatCompactVolume(active.lastPeriod)}</p>
              </div>
            </foreignObject>
          </g>
        ) : null}
      </svg>
    </article>
  );
}
