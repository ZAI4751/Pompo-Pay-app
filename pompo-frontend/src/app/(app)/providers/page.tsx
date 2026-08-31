import { PageShell } from "@/components/layout/PageShell";
import { ComingSoon } from "@/components/ui/ComingSoon";

export default function Page() {
  return (
    <PageShell title="Payment Providers" breadcrumb={[{ label: "Operations" }, { label: "Payment Providers" }]}>
      <ComingSoon feature="Payment Providers" />
    </PageShell>
  );
}
