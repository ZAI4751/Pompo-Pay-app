"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { PageShell } from "@/components/layout/PageShell";
import { SETTINGS_CATEGORIES, type SettingsCategoryId } from "@/lib/settings/catalog";
import { usePermissions } from "@/lib/auth/usePermissions";
import { cn } from "@/lib/utils/cn";
import { supportLabel, supportTone } from "./SettingPrimitives";
import { Badge } from "@/components/ui/Badge";

export function SettingsCategoryNav() {
  const pathname = usePathname();
  const { hasPermission } = usePermissions();

  return (
    <nav
      aria-label="Settings categories"
      className="mb-5 overflow-x-auto border-b border-border scrollbar-thin"
    >
      <ul className="flex min-w-max gap-1 pb-2">
        <li>
          <Link
            href="/settings"
            className={cn(
              "inline-flex rounded-lg px-3 py-1.5 text-[13px] font-medium",
              pathname === "/settings"
                ? "bg-primary-light text-primary"
                : "text-text-muted hover:bg-surface-inset hover:text-text",
            )}
            aria-current={pathname === "/settings" ? "page" : undefined}
          >
            Overview
          </Link>
        </li>
        {SETTINGS_CATEGORIES.map((category) => {
          if (category.permission && !hasPermission(category.permission)) return null;
          const active = pathname === category.href || pathname?.startsWith(`${category.href}/`);
          return (
            <li key={category.id}>
              <Link
                href={category.href}
                className={cn(
                  "inline-flex rounded-lg px-3 py-1.5 text-[13px] font-medium",
                  active
                    ? "bg-primary-light text-primary"
                    : "text-text-muted hover:bg-surface-inset hover:text-text",
                )}
                aria-current={active ? "page" : undefined}
              >
                {category.shortLabel}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}

export function SettingsShell({
  title,
  categoryId,
  actions,
  children,
}: {
  title: string;
  categoryId?: SettingsCategoryId;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  const category = categoryId
    ? SETTINGS_CATEGORIES.find((item) => item.id === categoryId)
    : undefined;
  const breadcrumb = category
    ? [
        { label: "Settings", href: "/settings" },
        { label: category.label },
      ]
    : [{ label: "Settings" }];

  return (
    <PageShell title={title} breadcrumb={breadcrumb} actions={actions}>
      <SettingsCategoryNav />
      {category && (
        <div className="mb-4 flex flex-wrap items-center gap-2">
          <Badge tone={supportTone(category.support)}>{supportLabel(category.support)}</Badge>
          <p className="text-sm text-text-muted">{category.description}</p>
        </div>
      )}
      <div className="space-y-4">{children}</div>
    </PageShell>
  );
}
