import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="API Keys" breadcrumb={[{ label: "Platform" }, { label: "API Keys" }]}>
      <ComingSoon feature="API Keys" />
    </PageShell>
  );
}
