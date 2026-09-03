import { Card, CardBody } from "./Card";

export function ComingSoon({ feature }: { feature: string }) {
  return (
    <BackendUnavailable
      feature={feature}
      detail="This surface is not available in this release. Nothing here is live production data."
    />
  );
}

export function BackendUnavailable({ feature, detail }: { feature: string; detail: string }) {
  return (
    <Card className="overflow-hidden">
      <div className="h-1 bg-warning" aria-hidden="true" />
      <CardBody className="flex flex-col items-center gap-2 px-6 py-16 text-center">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-warning">
          Not available in this release
        </p>
        <p className="text-sm font-semibold text-text">{feature}</p>
        <p className="max-w-lg break-words text-sm text-text-muted">{detail}</p>
      </CardBody>
    </Card>
  );
}
