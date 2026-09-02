"use client";

import { type InputHTMLAttributes, forwardRef, useId } from "react";
import { AnimatePresence, m } from "framer-motion";
import { cn } from "@/lib/utils/cn";
import { messageIn } from "@/lib/motion";

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  hint?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, label, error, hint, id, ...props }, ref) => {
    const generatedId = useId();
    const inputId = id ?? generatedId;
    const hintId = hint ? `${inputId}-hint` : undefined;
    const errorId = error ? `${inputId}-error` : undefined;

    return (
      <div className="flex min-w-0 flex-col gap-1.5">
        {label && (
          <label htmlFor={inputId} className="text-sm font-medium text-text">
            {label}
          </label>
        )}
        <input
          ref={ref}
          id={inputId}
          aria-invalid={Boolean(error)}
          aria-describedby={cn(hintId, errorId) || undefined}
          className={cn(
            "h-10 w-full min-w-0 rounded-xl border border-border-strong bg-white px-3 text-sm text-text",
            "placeholder:text-text-subtle transition-colors duration-200",
            "dark:bg-slate-900/80",
            "focus-visible:border-primary focus-visible:shadow-[0_0_0_4px_color-mix(in_srgb,var(--color-primary)_22%,transparent)]",
            error &&
              "border-error focus-visible:shadow-[0_0_0_4px_color-mix(in_srgb,var(--color-error)_20%,transparent)]",
            className,
          )}
          {...props}
        />
        {hint && !error && (
          <p id={hintId} className="break-words text-xs text-text-subtle">
            {hint}
          </p>
        )}
        <AnimatePresence>
          {error && (
            <m.p
              id={errorId}
              role="alert"
              className="text-xs text-error"
              initial={messageIn.initial}
              animate={messageIn.animate}
              exit={messageIn.exit}
              transition={messageIn.transition}
            >
              {error}
            </m.p>
          )}
        </AnimatePresence>
      </div>
    );
  },
);
Input.displayName = "Input";
