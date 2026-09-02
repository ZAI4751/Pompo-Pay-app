import type { Metadata } from "next";
import { ExperienceChrome } from "@/components/experience/ExperienceChrome";
import { InsightsDashboard } from "@/components/insights/InsightsDashboard";

export const metadata: Metadata = {
  title: "Pompo Insights",
  description: "Merchant insights dashboard preview for Pompo.",
};

export default function InsightsPage() {
  return (
    <ExperienceChrome>
      <InsightsDashboard />
    </ExperienceChrome>
  );
}
