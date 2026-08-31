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

/**
 * Reuses ApiErrorKind rather than defining a parallel vocabulary, so an
 * ApiError from the client can be rendered by passing `kind` straight
 * through -- there is no mapping table to fall out of sync.
 */
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
  /** Backend correlation ID, shown so a user can quote it in a bug report. */
  requestId?: string;
  onRetry?: () => void;
}

/** One consistent error presentation for every failure mode the app defines. */
export function ErrorState({
  kind = "unknown",
  description,
  requestId,
  onRetry,
}: ErrorStateProps) {
  const { icon: Icon, title } = config[kind];
  return (
    <div className="flex flex-col items-center justify-center gap-2 px-6 py-16 text-center">
      <Icon className="h-8 w-8 text-error" aria-hidden="true" />
      <p className="text-sm font-medium text-text">{title}</p>
      {description && <p className="max-w-sm text-sm text-text-muted">{description}</p>}
      {requestId && (
        <p className="text-xs text-text-subtle">
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
