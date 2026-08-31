import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Branches" breadcrumb={[{ label: "Merchants" }, { label: "Branches" }]}>
      <ComingSoon feature="Branches" />
    </PageShell>
  );
}
