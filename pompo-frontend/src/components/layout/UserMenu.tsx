"use client";

import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { ChevronDown, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";
import { cn } from "@/lib/utils/cn";

const MENU_WIDTH = 256;
const MENU_GAP = 8;

export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const [coords, setCoords] = useState({ top: 0, left: 0 });
  const buttonRef = useRef<HTMLButtonElement>(null);

  useLayoutEffect(() => {
    if (!open) return;

    const place = () => {
      const trigger = buttonRef.current;
      if (!trigger) return;
      const rect = trigger.getBoundingClientRect();
      const left = Math.min(
        Math.max(8, rect.right - MENU_WIDTH),
        window.innerWidth - MENU_WIDTH - 8,
      );
      setCoords({ top: rect.bottom + MENU_GAP, left });
    };

    place();
    window.addEventListener("resize", place);
    window.addEventListener("scroll", place, true);
    return () => {
      window.removeEventListener("resize", place);
      window.removeEventListener("scroll", place, true);
    };
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") setOpen(false);
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  if (!user) return null;

  const menu = open && typeof document !== "undefined"
    ? createPortal(
        <div className="fixed inset-0 z-[60]" role="presentation">
          <button
            type="button"
            className="absolute inset-0 cursor-default bg-transparent"
            aria-label="Close account menu"
            onClick={() => setOpen(false)}
          />
          <div
            role="menu"
            aria-label="Account"
            className={cn(
              "absolute w-64 overflow-hidden rounded-md border border-border bg-white py-1 shadow-glow pompo-glass",
              "dark:border-neutral-800 dark:bg-slate-900",
              "animate-fade-in",
            )}
            style={{ top: coords.top, left: coords.left }}
          >
            <div className="border-b border-border px-3 py-2.5">
              <p className="truncate text-sm font-medium text-text">{user.full_name}</p>
              <p className="truncate text-xs text-text-muted">{user.email}</p>
            </div>
            <button
              type="button"
              role="menuitem"
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text-muted"
              disabled
            >
              <UserIcon className="h-4 w-4" aria-hidden="true" />
              Profile
            </button>
            <button
              type="button"
              role="menuitem"
              onClick={() => {
                setOpen(false);
                void logout();
              }}
              className="flex w-full items-center gap-2 px-3 py-2 text-sm text-error hover:bg-error-bg"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </div>,
        document.body,
      )
    : null;

  return (
    <>
      <button
        ref={buttonRef}
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex max-w-[11rem] items-center gap-2 rounded-sm px-2 py-1.5 text-sm transition-colors duration-200 hover:bg-primary-light"
      >
        <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-sm bg-dark-blue text-xs font-semibold text-white">
          {user.full_name.charAt(0).toUpperCase()}
        </div>
        <span className="hidden min-w-0 truncate text-text sm:inline">{user.full_name}</span>
        <ChevronDown
          className={cn("h-3.5 w-3.5 shrink-0 text-text-subtle transition-transform duration-200", open && "rotate-180")}
          aria-hidden="true"
        />
      </button>
      {menu}
    </>
  );
}
