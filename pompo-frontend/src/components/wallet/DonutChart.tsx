"use client";

export function DonutChart({
  income,
  expense,
}: {
  income: number;
  expense: number;
}) {
  const total = Math.max(income + expense, 1);
  const radius = 42;
  const circ = 2 * Math.PI * radius;
  const incomeLen = (income / total) * circ;
  const expenseLen = (expense / total) * circ;

  return (
    <div className="flex items-center gap-5">
      <svg viewBox="0 0 120 120" className="h-28 w-28" role="img" aria-label="Income versus expense">
        <circle cx="60" cy="60" r={radius} fill="none" className="stroke-border" strokeWidth="14" />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          className="stroke-teal-400"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${incomeLen} ${circ - incomeLen}`}
          transform="rotate(-90 60 60)"
        />
        <circle
          cx="60"
          cy="60"
          r={radius}
          fill="none"
          className="stroke-orange-400"
          strokeWidth="14"
          strokeLinecap="round"
          strokeDasharray={`${expenseLen} ${circ - expenseLen}`}
          strokeDashoffset={-incomeLen}
          transform="rotate(-90 60 60)"
        />
        <circle cx="60" cy="60" r="26" className="fill-white dark:fill-slate-900" />
      </svg>
      <div className="space-y-3 text-sm">
        <Legend color="bg-teal-400" label="Income" value={income} />
        <Legend color="bg-orange-400" label="Expense" value={expense} />
      </div>
    </div>
  );
}

function Legend({ color, label, value }: { color: string; label: string; value: number }) {
  return (
    <div>
      <p className="flex items-center gap-2 text-text-muted">
        <span className={`h-2.5 w-2.5 rounded-full ${color}`} />
        {label}
      </p>
      <p className="text-lg font-bold tabular-nums text-text">
        MWK {value.toLocaleString("en-MW")}
      </p>
    </div>
  );
}
