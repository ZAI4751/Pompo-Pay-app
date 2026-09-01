import { cn } from "@/lib/utils/cn";

interface PompoMarkProps {
  className?: string;
  size?: number;
}

/** Geometric rail mark — a P built from payment-rail strokes on the brand blue. */
export function PompoMark({ className, size = 28 }: PompoMarkProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      className={cn("shrink-0", className)}
    >
      <rect width="32" height="32" rx="6" className="fill-primary" />
      <path
        d="M10 9.5h7.6c2.9 0 5.1 2 5.1 5.1 0 3.1-2.2 5.1-5.1 5.1H13.5"
        className="stroke-primary-foreground"
        strokeWidth="2.25"
        strokeLinecap="round"
      />
      <path
        d="M10 22.5h5.5"
        className="stroke-primary-foreground"
        strokeWidth="2.25"
        strokeLinecap="round"
      />
    </svg>
  );
}
