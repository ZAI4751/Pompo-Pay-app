import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Security" breadcrumb={[{ label: "Platform" }, { label: "Security" }]}>
      <ComingSoon feature="Security" />
    </PageShell>
  );
}
