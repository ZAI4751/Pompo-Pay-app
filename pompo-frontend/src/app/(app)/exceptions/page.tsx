import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Failed / Exceptions" breadcrumb={[{ label: "Operations" }, { label: "Failed / Exceptions" }]}>
      <ComingSoon feature="Failed / Exceptions" />
    </PageShell>
  );
}
