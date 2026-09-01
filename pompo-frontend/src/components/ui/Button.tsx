"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";
import { m } from "framer-motion";
import { Loader2 } from "lucide-react";
import { cn } from "@/lib/utils/cn";
import { buttonHover, buttonTap, pressSpring } from "@/lib/motion";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

type ButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"
> & {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
};

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-primary text-primary-foreground hover:bg-primary-hover shadow-sm dark:shadow-luminous",
  secondary:
    "bg-surface text-text border border-border-strong hover:bg-primary-light hover:border-primary dark:hover:shadow-luminous",
  ghost: "text-text-muted hover:bg-surface hover:text-text",
  danger: "bg-error text-white hover:opacity-90",
};

const sizeClasses: Record<Size, string> = {
  sm: "h-8 px-3 text-sm gap-1.5",
  md: "h-10 px-4 text-sm gap-2",
  lg: "h-11 px-5 text-base gap-2",
};

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = "primary", size = "md", loading, disabled, children, ...props }, ref) => {
    const isDisabled = Boolean(disabled || loading);
    return (
      <m.button
        ref={ref}
        disabled={isDisabled}
        whileHover={isDisabled ? undefined : buttonHover}
        whileTap={isDisabled ? undefined : buttonTap}
        transition={pressSpring}
        className={cn(
          "inline-flex items-center justify-center rounded-sm font-medium",
          "transition-colors duration-200",
          "disabled:opacity-50 disabled:cursor-not-allowed",
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
        {children}
      </m.button>
    );
  },
);
Button.displayName = "Button";
