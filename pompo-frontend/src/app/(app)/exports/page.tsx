import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Exports" breadcrumb={[{ label: "Reporting" }, { label: "Exports" }]}>
      <ComingSoon feature="Exports" />
    </PageShell>
  );
}
