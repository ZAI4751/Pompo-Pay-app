import Link from "next/link";
import { ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost";

interface BaseProps {
  children: ReactNode;
  variant?: Variant;
  className?: string;
  onClick?: () => void;
}

const base =
  "inline-flex items-center justify-center gap-2 rounded-full px-6 py-3 text-[15px] font-medium transition-all duration-300 focus-visible:outline-offset-4";

const variants: Record<Variant, string> = {
  primary:
    "bg-ink text-white hover:bg-indigo-600 active:scale-[0.98]",
  secondary:
    "border border-slate-line text-ink hover:border-ink bg-white active:scale-[0.98]",
  ghost: "text-ink hover:text-indigo-500",
};

export default function Button({
  children,
  href,
  variant = "primary",
  className = "",
  type = "button",
  disabled,
  onClick,
}: BaseProps & { href?: string; type?: "button" | "submit"; disabled?: boolean }) {
  const classes = `${base} ${variants[variant]} ${className} ${
    disabled ? "opacity-50 pointer-events-none" : ""
  }`;

  if (href) {
    return (
      <Link href={href} className={classes}>
        {children}
      </Link>
    );
  }

  return (
    <button type={type} disabled={disabled} onClick={onClick} className={classes}>
      {children}
    </button>
  );
}
