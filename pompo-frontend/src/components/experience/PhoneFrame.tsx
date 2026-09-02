import { cn } from "@/lib/utils/cn";

export function PhoneFrame({
  children,
  className,
}: {
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <div
      className={cn(
        "relative mx-auto flex h-[760px] w-full max-w-[390px] flex-col overflow-hidden rounded-[36px] border border-white/70 bg-white/35 shadow-[0_24px_80px_-32px_rgb(15_23_42_/_0.45)] backdrop-blur-xl",
        "dark:border-white/10 dark:bg-slate-950/40",
        className,
      )}
    >
      <div className="flex items-center justify-between px-6 pt-3 text-[11px] font-semibold text-text">
        <span className="tabular-nums">9:41</span>
        <span className="h-3.5 w-24 rounded-full bg-text/80" aria-hidden="true" />
        <span className="tabular-nums">5G</span>
      </div>
      <div className="flex min-h-0 flex-1 flex-col">{children}</div>
    </div>
  );
}
