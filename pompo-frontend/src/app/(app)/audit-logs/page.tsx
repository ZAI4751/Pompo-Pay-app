import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Audit" breadcrumb={[{ label: "Operations" }, { label: "Audit" }]}>
      <BackendUnavailable
        feature="Audit log list"
        detail="Services write immutable audit_logs rows, but there is no list or query API in this release. Open Settings → Audit for the documented gap. This screen will not invent events."
      />
    </PageShell>
  );
}
