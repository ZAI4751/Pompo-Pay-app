import type { LucideIcon } from "lucide-react";
import { Inbox } from "lucide-react";

interface EmptyStateProps {
  icon?: LucideIcon;
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ icon: Icon = Inbox, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-md border border-dashed border-border bg-slate-50 px-6 py-16 text-center dark:bg-slate-900/60">
      <div className="flex h-11 w-11 items-center justify-center rounded-md bg-primary-light text-primary">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <p className="max-w-sm break-words text-sm font-semibold text-text">{title}</p>
      {description && <p className="max-w-sm break-words text-sm text-text-muted">{description}</p>}
      {action && <div className="mt-2">{action}</div>}
    </div>
  );
}
