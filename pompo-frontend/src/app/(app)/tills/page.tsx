import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Tills" breadcrumb={[{ label: "Merchants" }, { label: "Tills" }]}>
      <ComingSoon feature="Tills" />
    </PageShell>
  );
}
