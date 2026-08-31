import { Construction } from "lucide-react";
import { Card } from "./Card";

/**
 * Placeholder for nav destinations whose backend milestone hasn't shipped
 * yet (Payments, Providers, Webhooks, System Health, etc.) -- shown instead
 * of a fake fully-built screen, per the spec's "do not expose every future
 * feature as if it already exists."
 */
export function ComingSoon({ feature }: { feature: string }) {
  return (
    <Card className="flex flex-col items-center gap-2 px-6 py-20 text-center">
      <Construction className="h-8 w-8 text-text-subtle" aria-hidden="true" />
      <p className="text-sm font-medium text-text">{feature} isn&apos;t available yet</p>
      <p className="max-w-sm text-sm text-text-muted">
        This screen is reserved for a future Pompo backend milestone. The navigation entry exists
        now so the information architecture doesn&apos;t need to be redesigned later.
      </p>
    </Card>
  );
}
