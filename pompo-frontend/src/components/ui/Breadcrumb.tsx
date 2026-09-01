import Link from "next/link";
import { ChevronRight } from "lucide-react";

interface Crumb {
  label: string;
  href?: string;
}

export function Breadcrumb({ items }: { items: Crumb[] }) {
  return (
    <nav aria-label="Breadcrumb" className="flex min-w-0 items-center gap-1.5 text-sm text-text-muted">
      {items.map((item, index) => (
        <span key={item.label} className="flex min-w-0 items-center gap-1.5">
          {index > 0 && <ChevronRight className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />}
          {item.href ? (
            <Link href={item.href} className="truncate hover:text-text hover:underline">
              {item.label}
            </Link>
          ) : (
            <span className="truncate font-medium text-text" aria-current="page">
              {item.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
