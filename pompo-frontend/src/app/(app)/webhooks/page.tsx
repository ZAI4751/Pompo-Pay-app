import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Webhooks" breadcrumb={[{ label: "Operations" }, { label: "Webhooks" }]}>
      <ComingSoon feature="Webhooks" />
    </PageShell>
  );
}
