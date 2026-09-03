import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Monitoring" breadcrumb={[{ label: "Configuration" }, { label: "Monitoring" }]}>
      <BackendUnavailable
        feature="Monitoring dashboard"
        detail="There is no dedicated monitoring API. Live checks are on System Health (GET /health). Provider health is on Providers."
      />
    </PageShell>
  );
}
