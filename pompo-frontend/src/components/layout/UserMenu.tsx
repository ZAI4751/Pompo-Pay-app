"use client";

import { useState, useRef, useEffect } from "react";
import { ChevronDown, LogOut, User as UserIcon } from "lucide-react";
import { useAuth } from "@/lib/auth/AuthContext";

export function UserMenu() {
  const { user, logout } = useAuth();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const onClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", onClickOutside);
    return () => document.removeEventListener("mousedown", onClickOutside);
  }, []);

  if (!user) return null;

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        aria-haspopup="menu"
        aria-expanded={open}
        className="flex items-center gap-2 rounded-sm px-2 py-1.5 text-sm hover:bg-primary-light"
      >
        <div className="flex h-7 w-7 items-center justify-center rounded-sm bg-dark-blue text-xs font-semibold text-white">
          {user.full_name.charAt(0).toUpperCase()}
        </div>
        <span className="hidden text-text sm:inline">{user.full_name}</span>
        <ChevronDown className="h-3.5 w-3.5 text-text-subtle" aria-hidden="true" />
      </button>
      {open && (
        <div
          role="menu"
          className="absolute right-0 top-full mt-1 w-56 rounded-sm border border-border bg-surface py-1 shadow-md animate-fade-in"
        >
          <div className="border-b border-border px-3 py-2">
            <p className="truncate text-sm font-medium text-text">{user.full_name}</p>
            <p className="truncate text-xs text-text-muted">{user.email}</p>
          </div>
          <button
            role="menuitem"
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-text hover:bg-surface-raised"
          >
            <UserIcon className="h-4 w-4" aria-hidden="true" />
            Profile
          </button>
          <button
            role="menuitem"
            onClick={() => void logout()}
            className="flex w-full items-center gap-2 px-3 py-2 text-sm text-error hover:bg-error-bg"
          >
            <LogOut className="h-4 w-4" aria-hidden="true" />
            Sign out
          </button>
        </div>
      )}
    </div>
  );
}
