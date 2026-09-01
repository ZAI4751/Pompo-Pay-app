import {
  CheckCircle2,
  CircleDashed,
  Clock,
  Loader2,
  MinusCircle,
  QrCode,
  ShieldAlert,
  TimerOff,
  Undo2,
  XCircle,
} from "lucide-react";
import { Badge } from "./Badge";
import { cn } from "@/lib/utils/cn";
import type { TransactionStatus } from "@/lib/types/transaction";

const config: Record<
  TransactionStatus,
  {
    label: string;
    tone: "success" | "warning" | "error" | "neutral" | "info";
    Icon: typeof CheckCircle2;
    pulse?: boolean;
  }
> = {
  created: { label: "Created", tone: "neutral", Icon: CircleDashed },
  qr_generated: { label: "QR generated", tone: "info", Icon: QrCode },
  pending: { label: "Pending", tone: "warning", Icon: Clock, pulse: true },
  pending_user_pin: { label: "Awaiting PIN", tone: "warning", Icon: ShieldAlert, pulse: true },
  processing: { label: "Processing", tone: "info", Icon: Loader2, pulse: true },
  success: { label: "Success", tone: "success", Icon: CheckCircle2 },
  failed: { label: "Failed", tone: "error", Icon: XCircle },
  timeout: { label: "Timed out", tone: "error", Icon: TimerOff },
  cancelled: { label: "Cancelled", tone: "neutral", Icon: MinusCircle },
  refunded: { label: "Refunded", tone: "info", Icon: Undo2 },
};

export function StatusBadge({ status }: { status: TransactionStatus }) {
  const { label, tone, Icon, pulse } = config[status];
  return (
    <Badge tone={tone} className="gap-1">
      <Icon className={cn("h-3 w-3", pulse && status === "processing" && "animate-spin")} />
      {label}
    </Badge>
  );
}

export function ActiveBadge({ isActive }: { isActive: boolean }) {
  return (
    <Badge tone={isActive ? "success" : "neutral"} className="gap-1">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          isActive ? "bg-success animate-pulse-dot" : "bg-text-subtle",
        )}
      />
      {isActive ? "Active" : "Inactive"}
    </Badge>
  );
}

export function HealthBadge({
  state,
}: {
  state: "healthy" | "degraded" | "down" | "unknown";
}) {
  const map = {
    healthy: { label: "Healthy", tone: "success" as const },
    degraded: { label: "Degraded", tone: "warning" as const },
    down: { label: "Down", tone: "error" as const },
    unknown: { label: "Unknown", tone: "neutral" as const },
  };
  const { label, tone } = map[state];
  return (
    <Badge tone={tone} className="gap-1">
      <span
        className={cn(
          "h-1.5 w-1.5 rounded-full",
          state === "healthy" && "bg-success animate-pulse-dot",
          state === "degraded" && "bg-warning",
          state === "down" && "bg-error",
          state === "unknown" && "bg-text-subtle",
        )}
      />
      {label}
    </Badge>
  );
}
