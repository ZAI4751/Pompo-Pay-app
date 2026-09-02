export function RepeatGauge({ value = 68, target = 80 }: { value?: number; target?: number }) {
  const ticks = 28;
  const filled = Math.round((value / 100) * ticks);

  return (
    <article className="rounded-3xl bg-white/85 p-5 shadow-[0_12px_40px_-28px_rgb(15_23_42_/_0.45)] backdrop-blur dark:bg-slate-900/70">
      <p className="text-sm font-semibold text-text">Settlement completion</p>
      <div className="relative mx-auto mt-2 h-32 w-56">
        <svg viewBox="0 0 200 110" className="h-full w-full" role="img" aria-label={`${value}% complete`}>
          {Array.from({ length: ticks }).map((_, index) => {
            const start = Math.PI;
            const angle = start + (index / (ticks - 1)) * Math.PI;
            const inner = 62;
            const outer = 82;
            const x1 = 100 + Math.cos(angle) * inner;
            const y1 = 100 + Math.sin(angle) * inner;
            const x2 = 100 + Math.cos(angle) * outer;
            const y2 = 100 + Math.sin(angle) * outer;
            const on = index < filled;
            return (
              <line
                key={index}
                x1={x1}
                y1={y1}
                x2={x2}
                y2={y2}
                stroke={on ? "#10b981" : "#e2e8f0"}
                strokeWidth="6"
                strokeLinecap="round"
              />
            );
          })}
        </svg>
        <p className="absolute inset-x-0 top-[52%] text-center text-3xl font-semibold tabular-nums text-text">
          {value}%
        </p>
      </div>
      <p className="text-center text-sm text-text-muted">On track for {target}% target</p>
      <button
        type="button"
        className="mt-4 w-full rounded-full border border-border bg-white py-2 text-sm font-semibold text-text transition hover:border-primary dark:bg-slate-900"
      >
        Show details
      </button>
    </article>
  );
}
