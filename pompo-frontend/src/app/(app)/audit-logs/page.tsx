import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Audit Logs" breadcrumb={[{ label: "Platform" }, { label: "Audit Logs" }]}>
      <ComingSoon feature="Audit Logs" />
    </PageShell>
  );
}
