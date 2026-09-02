"use client";

import { useState } from "react";
import { WalletHome } from "./WalletHome";
import { WalletAssistant } from "./WalletAssistant";
import { WalletPayment } from "./WalletPayment";
import { WalletProfile } from "./WalletProfile";
import { WalletNav } from "./WalletNav";
import { ScanModal } from "./ScanModal";
import { MoneySheet } from "./MoneySheet";
import { PhoneFrame } from "@/components/experience/PhoneFrame";
import type { ChatMessage, WalletTab } from "@/lib/experience/data";
import { expenseTotal, incomeTotal } from "@/lib/experience/data";
import { useExperienceData } from "@/lib/experience/useExperienceData";
import { ErrorState } from "@/components/ui/ErrorState";

export function WalletApp({ lockedTab }: { lockedTab?: WalletTab }) {
  const { data, error, loading } = useExperienceData();
  const [tab, setTab] = useState<WalletTab>(lockedTab ?? "home");
  const [hidden, setHidden] = useState(false);
  const [scanOpen, setScanOpen] = useState(false);
  const [money, setMoney] = useState<"send" | "request" | null>(null);
  const [chat, setChat] = useState<ChatMessage[] | null>(null);

  const messages = chat ?? data?.chat ?? [];
  const active = lockedTab ?? tab;

  function go(next: WalletTab) {
    if (!lockedTab) setTab(next);
  }

  let screen;
  if (error) {
    screen = (
      <div className="p-4">
        <ErrorState kind="unavailable" description={error} />
      </div>
    );
  } else if (active === "assistant") {
    screen = (
      <WalletAssistant
        messages={messages}
        txns={data?.txns ?? []}
        onSend={(text) =>
          setChat((current) => [
            ...(current ?? data?.chat ?? []),
            { id: `u-${Date.now()}`, role: "user", body: text },
            {
              id: `a-${Date.now()}`,
              role: "assistant",
              body: "I can explain spend, but I cannot move money from this preview. Open Insights for volume, or scan a QR in the mobile app to pay.",
            },
          ])
        }
        onSuggestion={(id) => {
          if (id === "hist") go("payment");
          else {
            setChat((current) => [
              ...(current ?? data?.chat ?? []),
              {
                id: `s-${Date.now()}`,
                role: "assistant",
                body: `Income MWK ${incomeTotal.toLocaleString("en-MW")} versus expense MWK ${expenseTotal.toLocaleString("en-MW")} this period.`,
              },
            ]);
          }
        }}
      />
    );
  } else if (active === "payment") {
    screen = (
      <WalletPayment bills={data?.bills ?? []} txns={data?.txns ?? []} onBack={() => go("home")} />
    );
  } else if (active === "profile") {
    screen = <WalletProfile />;
  } else {
    screen = (
      <WalletHome
        balance={data?.balance ?? 0}
        hidden={hidden}
        onToggle={() => setHidden((value) => !value)}
        txns={data?.txns ?? []}
        loading={loading}
        onSeeMore={() => go("payment")}
        onSend={() => setMoney("send")}
        onRequest={() => setMoney("request")}
      />
    );
  }

  return (
    <PhoneFrame>
      {screen}
      <WalletNav active={active} onChange={go} onScan={() => setScanOpen(true)} />
      <ScanModal open={scanOpen} onClose={() => setScanOpen(false)} />
      <MoneySheet open={money !== null} mode={money ?? "send"} onClose={() => setMoney(null)} />
    </PhoneFrame>
  );
}
