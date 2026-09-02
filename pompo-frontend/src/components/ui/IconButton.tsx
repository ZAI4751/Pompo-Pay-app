"use client";

import { type ButtonHTMLAttributes, forwardRef } from "react";
import { m } from "framer-motion";
import { cn } from "@/lib/utils/cn";
import { pressSpring } from "@/lib/motion";

type IconButtonProps = Omit<
  ButtonHTMLAttributes<HTMLButtonElement>,
  "onDrag" | "onDragStart" | "onDragEnd" | "onAnimationStart"
> & {
  "aria-label": string;
};

export const IconButton = forwardRef<HTMLButtonElement, IconButtonProps>(
  ({ className, disabled, ...props }, ref) => (
    <m.button
      ref={ref}
      disabled={disabled}
      whileHover={disabled ? undefined : { scale: 1.03 }}
      whileTap={disabled ? undefined : { scale: 0.97 }}
      transition={pressSpring}
      className={cn(
        "inline-flex h-9 w-9 items-center justify-center rounded-xl text-text-muted",
        "hover:bg-primary-light hover:text-text",
        "transition-colors duration-200",
        "disabled:opacity-50 disabled:cursor-not-allowed",
        className,
      )}
      {...props}
    />
  ),
);
IconButton.displayName = "IconButton";
