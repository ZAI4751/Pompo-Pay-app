import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Analytics" breadcrumb={[{ label: "Operations" }, { label: "Analytics" }]}>
      <BackendUnavailable
        feature="Analytics"
        detail="There is no analytics or volume-chart API. Dashboard metrics come from live merchant, provider, customer-stats, webhook, settlement, and reconciliation endpoints only."
      />
    </PageShell>
  );
}
