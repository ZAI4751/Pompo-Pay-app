import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Analytics" breadcrumb={[{ label: "Reporting" }, { label: "Analytics" }]}>
      <ComingSoon feature="Analytics" />
    </PageShell>
  );
}
