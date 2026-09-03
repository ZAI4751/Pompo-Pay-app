import { PageShell } from "@/components/layout/PageShell";
import { BackendUnavailable } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Exports" breadcrumb={[{ label: "Operations" }, { label: "Exports" }]}>
      <BackendUnavailable
        feature="Exports"
        detail="There is no export or download API in this release. This console will not generate CSV or PDF files from invented data."
      />
    </PageShell>
  );
}
