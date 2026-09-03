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

export function paymentStatusDetail(status: string, serverDetail?: string | null): string {
  if (serverDetail && serverDetail.trim()) {
    return serverDetail;
  }
  switch (mapPaymentStatus(status)) {
    case "success":
      return "This payment completed successfully.";
    case "failed":
      return status === "cancelled" ? "This payment was cancelled." : "This payment did not go through.";
    case "timeout":
      return "We haven't received a final response yet.";
    case "processing":
      return "Your payment is being processed.";
    case "pending":
      return "We're waiting for the payment to continue.";
    case "awaiting_confirmation":
      return "Your payment is ready to start.";
    default:
      return "We're checking the payment status.";
  }
}
