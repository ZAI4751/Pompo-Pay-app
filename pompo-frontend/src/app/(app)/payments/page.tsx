import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Payments" breadcrumb={[{ label: "Operations" }, { label: "Payments" }]}>
      <ComingSoon feature="Payments" />
    </PageShell>
  );
}
