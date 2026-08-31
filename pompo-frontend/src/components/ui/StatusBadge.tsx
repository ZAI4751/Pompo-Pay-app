import { Badge } from "./Badge";
import type { TransactionStatus } from "@/lib/types/transaction";

const config: Record<TransactionStatus, { label: string; tone: "success" | "warning" | "error" | "neutral" | "info" }> = {
  created: { label: "Created", tone: "neutral" },
  qr_generated: { label: "QR Generated", tone: "info" },
  pending: { label: "Pending", tone: "warning" },
  pending_user_pin: { label: "Awaiting PIN", tone: "warning" },
  processing: { label: "Processing", tone: "info" },
  success: { label: "Success", tone: "success" },
  failed: { label: "Failed", tone: "error" },
  timeout: { label: "Timed Out", tone: "error" },
  cancelled: { label: "Cancelled", tone: "neutral" },
  refunded: { label: "Refunded", tone: "info" },
};

/** Renders a Transaction's status with the right color -- one source of truth. */
export function StatusBadge({ status }: { status: TransactionStatus }) {
  const { label, tone } = config[status];
  return <Badge tone={tone}>{label}</Badge>;
}

/** Simple active/inactive variant reused across Merchants, Branches, Users. */
export function ActiveBadge({ isActive }: { isActive: boolean }) {
  return <Badge tone={isActive ? "success" : "neutral"}>{isActive ? "Active" : "Inactive"}</Badge>;
}
