import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="System Settings" breadcrumb={[{ label: "Platform" }, { label: "System Settings" }]}>
      <ComingSoon feature="System Settings" />
    </PageShell>
  );
}
