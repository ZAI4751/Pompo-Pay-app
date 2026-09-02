"use client";

import { useState } from "react";
import { InsightsSidebar } from "./InsightsSidebar";
import { InsightsHeader } from "./InsightsHeader";
import { KpiCard } from "./KpiCard";
import { VolumeChart } from "./VolumeChart";
import { ActiveDayChart } from "./ActiveDayChart";
import { RepeatGauge } from "./RepeatGauge";
import { MerchantTable } from "./MerchantTable";
import { AssistantPanel } from "./AssistantPanel";
import { SegmentStrip } from "./SegmentStrip";
import { useExperienceData } from "@/lib/experience/useExperienceData";
import { useToast } from "@/components/ui/Toast";
import { ErrorState } from "@/components/ui/ErrorState";

export function InsightsDashboard() {
  const { data, error, loading } = useExperienceData(400);
  const { push } = useToast();
  const [period, setPeriod] = useState<"7d" | "30d">("30d");
  const [menu, setMenu] = useState(false);

  if (error) {
    return (
      <div className="p-8">
        <ErrorState kind="unavailable" description={error} />
      </div>
    );
  }

  const kpis = data?.kpis ?? [];
  const volume = period === "7d" ? (data?.volume ?? []).slice(-4) : (data?.volume ?? []);

  return (
    <div className="flex min-h-[calc(100vh-57px)]">
      {menu ? (
        <button
          type="button"
          aria-label="Close navigation"
          className="fixed inset-0 z-30 bg-slate-950/30 lg:hidden"
          onClick={() => setMenu(false)}
        />
      ) : null}
      <InsightsSidebar open={menu} onNavigate={() => setMenu(false)} />
      <div className="min-w-0 flex-1 overflow-x-hidden p-4 sm:p-6 lg:p-8">
        <InsightsHeader
          period={period}
          onPeriod={setPeriod}
          onMenu={() => setMenu(true)}
          onExport={() => push("Export is a preview action. No file left this browser.", "info")}
        />

        <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
          {(loading ? placeholderKpis : kpis).map((kpi) => (
            <KpiCard key={kpi.id} kpi={kpi} loading={loading} />
          ))}
        </div>

        <div className="mt-4 grid gap-4 xl:grid-cols-[minmax(0,1.6fr)_minmax(280px,0.8fr)]">
          <div className="space-y-4">
            <VolumeChart data={volume} />
            <SegmentStrip title="Payment rails" items={data?.rails ?? []} />
            <MerchantTable rows={data?.merchants ?? []} loading={loading} />
          </div>
          <div className="space-y-4">
            <ActiveDayChart days={data?.weekdays ?? []} />
            <RepeatGauge />
            <AssistantPanel />
          </div>
        </div>
      </div>
    </div>
  );
}

const placeholderKpis = [
  { id: "p1", label: "Payments", value: "—", delta: 0, icon: "eye" as const },
  { id: "p2", label: "Active payers", value: "—", delta: 0, icon: "users" as const },
  { id: "p3", label: "QR scans", value: "—", delta: 0, icon: "pointer" as const },
  { id: "p4", label: "Settled payouts", value: "—", delta: 0, icon: "inbox" as const },
];
