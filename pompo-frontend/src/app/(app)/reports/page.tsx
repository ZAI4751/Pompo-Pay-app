import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Reports" breadcrumb={[{ label: "Reporting" }, { label: "Reports" }]}>
      <ComingSoon feature="Reports" />
    </PageShell>
  );
}
