import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Reports" breadcrumb={[{ label: "Operations" }, { label: "Reports" }]}>
      <BackendUnavailable
        feature="Reports"
        detail="There is no reports API. Use Payments lookup, Settlements, and Reconciliation for operational figures that already exist."
      />
    </PageShell>
  );
}
