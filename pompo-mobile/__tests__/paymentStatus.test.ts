import { isTerminalPayment, mapPaymentStatus, paymentStatusLabel } from "@/domain/paymentStatus";

describe("payment status mapping", () => {
  it("maps backend statuses without inventing new financial states", () => {
    expect(mapPaymentStatus("qr_generated")).toBe("awaiting_confirmation");
    expect(mapPaymentStatus("pending")).toBe("pending");
    expect(mapPaymentStatus("processing")).toBe("processing");
    expect(mapPaymentStatus("success")).toBe("success");
    expect(mapPaymentStatus("failed")).toBe("failed");
    expect(mapPaymentStatus("timeout")).toBe("timeout");
    expect(mapPaymentStatus("mystery")).toBe("unknown");
  });

  it("treats success failed and timeout as terminal", () => {
    expect(isTerminalPayment("success")).toBe(true);
    expect(isTerminalPayment("pending")).toBe(false);
  });

  it("labels cancelled as cancelled", () => {
    expect(paymentStatusLabel("cancelled")).toBe("Cancelled");
  });
});
