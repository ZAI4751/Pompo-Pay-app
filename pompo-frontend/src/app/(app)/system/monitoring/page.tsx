import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Monitoring" breadcrumb={[{ label: "System" }, { label: "Monitoring" }]}>
      <ComingSoon feature="Monitoring" />
    </PageShell>
  );
}
