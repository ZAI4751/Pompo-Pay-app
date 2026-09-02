export type PaymentUiPhase =
  | "awaiting_confirmation"
  | "initiating"
  | "pending"
  | "processing"
  | "success"
  | "failed"
  | "timeout"
  | "unknown";

const PHASE_BY_STATUS: Record<string, PaymentUiPhase> = {
  created: "awaiting_confirmation",
  qr_generated: "awaiting_confirmation",
  pending: "pending",
  pending_user_pin: "pending",
  processing: "processing",
  success: "success",
  failed: "failed",
  cancelled: "failed",
  refunded: "failed",
  timeout: "timeout",
};

export function mapPaymentStatus(status: string): PaymentUiPhase {
  return PHASE_BY_STATUS[status] ?? "unknown";
}

export function isTerminalPayment(status: string): boolean {
  const phase = mapPaymentStatus(status);
  return phase === "success" || phase === "failed" || phase === "timeout";
}

export function paymentStatusLabel(status: string): string {
  switch (mapPaymentStatus(status)) {
    case "success":
      return "Paid";
    case "failed":
      return status === "cancelled" ? "Cancelled" : "Failed";
    case "timeout":
      return "Timed out";
    case "processing":
      return "Processing";
    case "pending":
      return "Pending";
    case "awaiting_confirmation":
      return "Awaiting payment";
    default:
      return "Needs confirmation";
  }
}
