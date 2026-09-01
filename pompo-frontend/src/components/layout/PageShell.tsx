import { TopBar } from "./TopBar";

interface PageShellProps {
  title: string;
  breadcrumb: { label: string; href?: string }[];
  actions?: React.ReactNode;
  children: React.ReactNode;
}

/** Standard page wrapper: integrated top bar + scrollable operational canvas. */
export function PageShell({ title, breadcrumb, actions, children }: PageShellProps) {
  return (
    <>
      <TopBar title={title} breadcrumb={breadcrumb} actions={actions} />
      <main className="relative flex-1 overflow-y-auto scrollbar-thin">
        <div className="pompo-aurora pointer-events-none absolute inset-0" aria-hidden="true" />
        <div className="relative animate-fade-up p-5 lg:p-6">{children}</div>
      </main>
    </>
  );
}
