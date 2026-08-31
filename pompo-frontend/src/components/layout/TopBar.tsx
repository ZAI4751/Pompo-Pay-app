"use client";

import { Bell } from "lucide-react";
import { ThemeToggle } from "./ThemeToggle";
import { UserMenu } from "./UserMenu";
import { IconButton } from "@/components/ui/IconButton";
import { Badge } from "@/components/ui/Badge";

export function TopBar({ title }: { title: string }) {
  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-border bg-surface px-5">
      <h1 className="text-sm font-semibold text-text">{title}</h1>
      <div className="flex items-center gap-1.5">
        <Badge tone="warning" className="mr-2 hidden sm:inline-flex">
          Development
        </Badge>
        <IconButton aria-label="Notifications">
          <Bell className="h-4 w-4" />
        </IconButton>
        <ThemeToggle />
        <div className="mx-1 h-6 w-px bg-border" aria-hidden="true" />
        <UserMenu />
      </div>
    </header>
  );
}
