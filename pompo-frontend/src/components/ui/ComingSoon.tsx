import { Construction } from "lucide-react";
import { Card, CardBody } from "./Card";

export function ComingSoon({ feature }: { feature: string }) {
  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-primary" aria-hidden="true" />
      <CardBody className="flex flex-col items-center gap-2 px-6 py-20 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-md bg-primary-light text-primary">
          <Construction className="h-6 w-6" aria-hidden="true" />
        </div>
        <p className="text-sm font-semibold text-text">{feature} is reserved</p>
        <p className="max-w-md text-sm text-text-muted">
          MOCK — BACKEND NOT YET AVAILABLE. This surface is in the information architecture so
          operations can navigate here later. Nothing here is live production data.
        </p>
      </CardBody>
    </Card>
  );
}

export function BackendUnavailable({ feature, detail }: { feature: string; detail: string }) {
  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-warning" aria-hidden="true" />
      <CardBody className="flex flex-col items-center gap-2 px-6 py-16 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-warning">
          MOCK — BACKEND NOT YET AVAILABLE
        </p>
        <p className="text-sm font-semibold text-text">{feature}</p>
        <p className="max-w-lg text-sm text-text-muted">{detail}</p>
      </CardBody>
    </Card>
  );
}
