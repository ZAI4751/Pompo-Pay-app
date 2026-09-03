import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Services" breadcrumb={[{ label: "Configuration" }, { label: "Services" }]}>
      <BackendUnavailable
        feature="Service catalog"
        detail="There is no services-management API. Use System Health and Settings → System for process configuration that actually runs."
      />
    </PageShell>
  );
}
