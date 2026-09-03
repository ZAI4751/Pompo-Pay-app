import { activeTabFromPathname, shouldShowBottomNav } from "@/domain/appShell";

describe("app shell bottom navigation", () => {
  test("shows the persistent bar on primary shell routes including scan", () => {
    expect(shouldShowBottomNav("/customer")).toBe(true);
    expect(shouldShowBottomNav("/customer/history")).toBe(true);
    expect(shouldShowBottomNav("/customer/profile")).toBe(true);
    expect(shouldShowBottomNav("/customer/notifications")).toBe(true);
    expect(shouldShowBottomNav("/customer/scan")).toBe(true);
    expect(shouldShowBottomNav("/customer/methods")).toBe(true);
    expect(shouldShowBottomNav("/customer/requests")).toBe(true);
    expect(shouldShowBottomNav("/merchant")).toBe(true);
    expect(shouldShowBottomNav("/merchant/activity")).toBe(true);
    expect(shouldShowBottomNav("/merchant/profile")).toBe(true);
    expect(shouldShowBottomNav("/merchant/qr")).toBe(true);
  });

  test("hides the bar on immersive payment and detail flows", () => {
    expect(shouldShowBottomNav("/customer/preview")).toBe(false);
    expect(shouldShowBottomNav("/customer/confirm")).toBe(false);
    expect(shouldShowBottomNav("/customer/processing")).toBe(false);
    expect(shouldShowBottomNav("/customer/result")).toBe(false);
    expect(shouldShowBottomNav("/customer/payment/PMP-1")).toBe(false);
    expect(shouldShowBottomNav("/customer/methods/add")).toBe(false);
    expect(shouldShowBottomNav("/customer/methods/PIM-1")).toBe(false);
    expect(shouldShowBottomNav("/customer/requests/REQ-1")).toBe(false);
    expect(shouldShowBottomNav("/customer/pay-request/REQ-1")).toBe(false);
    expect(shouldShowBottomNav("/merchant/payment/PMP-1")).toBe(false);
    expect(shouldShowBottomNav("/merchant/qr/QRABC123456789")).toBe(false);
  });

  test("maps routes to the correct active tab", () => {
    expect(activeTabFromPathname("/customer")).toBe("home");
    expect(activeTabFromPathname("/customer/scan")).toBe("home");
    expect(activeTabFromPathname("/customer/history")).toBe("history");
    expect(activeTabFromPathname("/customer/requests")).toBe("history");
    expect(activeTabFromPathname("/customer/profile")).toBe("profile");
    expect(activeTabFromPathname("/customer/notifications")).toBe("profile");
    expect(activeTabFromPathname("/merchant")).toBe("home");
    expect(activeTabFromPathname("/merchant/activity")).toBe("activity");
    expect(activeTabFromPathname("/merchant/profile")).toBe("profile");
    expect(activeTabFromPathname("/merchant/qr")).toBe("qr");
  });
});
