import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Services" breadcrumb={[{ label: "System" }, { label: "Services" }]}>
      <ComingSoon feature="Services" />
    </PageShell>
  );
}
