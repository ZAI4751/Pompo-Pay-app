import {
  AlertTriangle,
  Clock,
  FileWarning,
  Lock,
  SearchX,
  ServerCrash,
  ShieldAlert,
  WifiOff,
} from "lucide-react";
import { Button } from "./Button";
import type { ApiErrorKind } from "@/lib/types/common";

const config: Record<ApiErrorKind, { icon: typeof AlertTriangle; title: string }> = {
  network: { icon: WifiOff, title: "Couldn't reach the Pompo backend" },
  unauthorized: { icon: Lock, title: "Your session has expired" },
  forbidden: { icon: ShieldAlert, title: "You don't have access to this" },
  not_found: { icon: SearchX, title: "Nothing found here" },
  conflict: { icon: FileWarning, title: "That conflicts with the current state" },
  validation: { icon: FileWarning, title: "Some values need attention" },
  rate_limited: { icon: Clock, title: "Too many requests" },
  server: { icon: ServerCrash, title: "The server hit an error" },
  unavailable: { icon: ServerCrash, title: "Service temporarily unavailable" },
  unknown: { icon: AlertTriangle, title: "Something went wrong" },
};

interface ErrorStateProps {
  kind?: ApiErrorKind;
  description?: string;
  requestId?: string;
  onRetry?: () => void;
}

export function ErrorState({
  kind = "unknown",
  description,
  requestId,
  onRetry,
}: ErrorStateProps) {
  const { icon: Icon, title } = config[kind];
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-error/25 bg-error-bg/40 px-6 py-16 text-center">
      <div className="flex h-11 w-11 items-center justify-center rounded-md bg-error-bg text-error">
        <Icon className="h-5 w-5" aria-hidden="true" />
      </div>
      <p className="max-w-sm break-words text-sm font-semibold text-text">{title}</p>
      {description && <p className="max-w-sm break-words text-sm text-text-muted">{description}</p>}
      {requestId && (
        <p className="max-w-full truncate text-xs text-text-subtle">
          Reference: <span className="font-mono">{requestId}</span>
        </p>
      )}
      {onRetry && (
        <Button variant="secondary" size="sm" className="mt-2" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}
