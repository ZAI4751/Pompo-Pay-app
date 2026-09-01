"use client";

interface SeriesPoint {
  label: string;
  volume: number;
  count: number;
  failed: number;
}

interface AreaChartProps {
  data: SeriesPoint[];
  metric: "volume" | "count";
}

function pathFrom(values: number[], width: number, height: number): string {
  const max = Math.max(...values, 1);
  return values
    .map((value, index) => {
      const x = (index / Math.max(values.length - 1, 1)) * width;
      const y = height - (value / max) * (height - 16) - 8;
      return `${index === 0 ? "M" : "L"}${x.toFixed(1)} ${y.toFixed(1)}`;
    })
    .join(" ");
}

export function TransactionAreaChart({ data, metric }: AreaChartProps) {
  const width = 720;
  const plotHeight = 200;
  const height = 228;
  const values = data.map((point) => (metric === "volume" ? point.volume : point.count));
  const failValues = data.map((point) => point.failed);
  const line = pathFrom(values, width, plotHeight);
  const failLine = pathFrom(failValues, width, plotHeight);
  const area = `${line} L${width} ${plotHeight} L0 ${plotHeight} Z`;
  const max = Math.max(...values, 1);

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-[240px] w-full"
      role="img"
      aria-label={metric === "volume" ? "Transaction volume trend" : "Transaction count trend"}
    >
      <defs>
        <linearGradient id="pompo-chart-fill" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="var(--color-primary)" stopOpacity="0.28" />
          <stop offset="100%" stopColor="var(--color-primary)" stopOpacity="0.02" />
        </linearGradient>
      </defs>
      {[0.25, 0.5, 0.75].map((frac) => (
        <line
          key={frac}
          x1="0"
          x2={width}
          y1={plotHeight * frac}
          y2={plotHeight * frac}
          className="stroke-border"
          strokeWidth="1"
        />
      ))}
      <path d={area} fill="url(#pompo-chart-fill)" className="motion-safe:animate-fade-in" />
      <path
        d={line}
        fill="none"
        className="stroke-primary motion-safe:animate-fade-in"
        strokeWidth="2.2"
        strokeLinejoin="round"
        strokeLinecap="round"
      />
      <path
        d={failLine}
        fill="none"
        className="stroke-error/70"
        strokeWidth="1.4"
        strokeDasharray="4 4"
      />
      {data.map((point, index) => {
        const x = (index / Math.max(data.length - 1, 1)) * width;
        const value = values[index] ?? 0;
        const y = plotHeight - (value / max) * (plotHeight - 16) - 8;
        return (
          <g key={`${point.label}-${metric}`}>
            <circle cx={x} cy={y} r="2.4" className="fill-primary" />
            <text
              x={x}
              y={height - 6}
              textAnchor="middle"
              className="fill-text-subtle"
              fontSize="11"
            >
              {point.label}
            </text>
          </g>
        );
      })}
    </svg>
  );
}

export function ChartLegend() {
  return (
    <div className="flex flex-wrap gap-4 text-[11px] text-text-muted">
      <span className="flex items-center gap-1.5">
        <span className="h-0.5 w-4 bg-primary" /> Volume / count
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-px w-4 border-t border-dashed border-error" /> Failed
      </span>
    </div>
  );
}
