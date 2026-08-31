import { TopBar } from "./TopBar";
import { Breadcrumb } from "@/components/ui/Breadcrumb";

interface PageShellProps {
  title: string;
  breadcrumb: { label: string; href?: string }[];
  actions?: React.ReactNode;
  children: React.ReactNode;
}

/** Standard page wrapper: TopBar + breadcrumb/actions row + scrollable content. */
export function PageShell({ title, breadcrumb, actions, children }: PageShellProps) {
  return (
    <>
      <TopBar title={title} />
      <main className="flex-1 overflow-y-auto scrollbar-thin">
        <div className="flex items-center justify-between border-b border-border bg-surface px-5 py-3">
          <Breadcrumb items={breadcrumb} />
          {actions}
        </div>
        <div className="p-5">{children}</div>
      </main>
    </>
  );
}
