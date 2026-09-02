import { ShieldCheck } from "lucide-react";

export function WalletProfile() {
  return (
    <div className="flex min-h-0 flex-1 flex-col overflow-y-auto px-5 pb-2 pt-6 scrollbar-thin">
      <div className="mx-auto flex h-20 w-20 items-center justify-center rounded-full bg-gradient-to-br from-primary to-violet-400 text-xl font-bold text-white">
        GP
      </div>
      <h1 className="mt-4 text-center text-xl font-semibold text-text">Grace Phiri</h1>
      <p className="text-center text-sm text-text-muted">Customer · Lilongwe</p>
      <div className="mt-6 space-y-3">
        {[
          ["Phone", "+265 991 000 001"],
          ["KYC", "Verified"],
          ["Default rail", "Airtel Money"],
        ].map(([label, value]) => (
          <div key={label} className="flex items-center justify-between rounded-2xl bg-white/80 px-4 py-3 dark:bg-slate-900/70">
            <span className="text-sm text-text-muted">{label}</span>
            <span className="text-sm font-semibold text-text">{value}</span>
          </div>
        ))}
      </div>
      <p className="mt-6 flex items-center justify-center gap-2 text-xs text-text-subtle">
        <ShieldCheck className="h-4 w-4 text-success" />
        Profile actions are UX only. Authorization stays on the server.
      </p>
    </div>
  );
}
