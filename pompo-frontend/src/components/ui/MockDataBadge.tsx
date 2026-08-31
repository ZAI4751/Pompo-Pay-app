import { FlaskConical } from "lucide-react";
import { Badge } from "./Badge";

/**
 * Required visual indicator on every screen backed by src/mocks --
 * demo/mock data must never be presented as real (see spec, "Dashboard").
 */
export function MockDataBadge() {
  return (
    <Badge tone="warning" className="gap-1">
      <FlaskConical className="h-3 w-3" aria-hidden="true" />
      Demo data
    </Badge>
  );
}
