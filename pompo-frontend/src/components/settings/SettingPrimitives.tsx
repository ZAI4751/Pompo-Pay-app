"use client";

import Link from "next/link";
import { Badge } from "@/components/ui/Badge";
import { Button } from "@/components/ui/Button";
import { Card, CardBody, CardHeader, CardTitle } from "@/components/ui/Card";
import { cn } from "@/lib/utils/cn";
import type { SettingsSupport } from "@/lib/settings/catalog";

export function supportTone(support: SettingsSupport): "success" | "warning" | "neutral" {
  if (support === "live") return "success";
  if (support === "partial") return "warning";
  return "neutral";
}

export function supportLabel(support: SettingsSupport): string {
  if (support === "live") return "Live API";
  if (support === "partial") return "Partial";
  return "Backend gap";
}

export function SettingRow({
  label,
  value,
  hint,
  source,
}: {
  label: string;
  value: React.ReactNode;
  hint?: string;
  source?: "api" | "environment" | "local" | "session";
}) {
  return (
    <div className="grid gap-1 border-b border-border py-3 last:border-b-0 sm:grid-cols-[minmax(11rem,16rem)_1fr] sm:gap-6">
      <div>
        <p className="text-sm font-medium text-text">{label}</p>
        {hint && <p className="mt-0.5 text-xs text-text-subtle">{hint}</p>}
      </div>
      <div className="min-w-0">
        <div className="break-words text-sm text-text">{value}</div>
        {source && (
          <p className="mt-1 text-[11px] uppercase tracking-[0.12em] text-text-subtle">
            {source === "environment" && "Environment · read-only"}
            {source === "api" && "Live API"}
            {source === "local" && "This device only"}
            {source === "session" && "Signed-in session"}
          </p>
        )}
      </div>
    </div>
  );
}

export function MonoValue({ children }: { children: React.ReactNode }) {
  return <span className="font-mono text-[13px] text-text">{children}</span>;
}

export function BackendGapCard({
  title,
  contract,
  detail,
}: {
  title: string;
  contract: string;
  detail: string;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-warning" aria-hidden="true" />
      <CardHeader>
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-warning">
            Backend gap
          </p>
          <CardTitle className="mt-1">{title}</CardTitle>
        </div>
        <Badge tone="warning">Not exposed</Badge>
      </CardHeader>
      <CardBody className="space-y-2 text-sm text-text-muted">
        <p>{detail}</p>
        <p className="font-mono text-xs text-text-subtle">{contract}</p>
      </CardBody>
    </Card>
  );
}

export function ModuleLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="inline-flex items-center rounded-lg border border-border px-2.5 py-1 text-xs font-medium text-text hover:border-primary hover:text-primary"
    >
      {children}
    </Link>
  );
}

export function SettingsPanel({
  title,
  description,
  badge,
  actions,
  children,
}: {
  title: string;
  description: string;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <CardTitle>{title}</CardTitle>
            {badge}
          </div>
          <p className="mt-1 text-sm text-text-muted">{description}</p>
        </div>
        {actions}
      </CardHeader>
      <CardBody className={cn("space-y-1")}>{children}</CardBody>
    </Card>
  );
}

export function FormActions({
  dirty,
  saving,
  onCancel,
  saveLabel = "Save",
}: {
  dirty: boolean;
  saving: boolean;
  onCancel: () => void;
  saveLabel?: string;
}) {
  return (
    <div className="flex items-center justify-end gap-2 border-t border-border pt-4">
      <Button type="button" variant="secondary" size="sm" onClick={onCancel} disabled={!dirty || saving}>
        Cancel
      </Button>
      <Button type="submit" size="sm" loading={saving} disabled={!dirty}>
        {saveLabel}
      </Button>
    </div>
  );
}
