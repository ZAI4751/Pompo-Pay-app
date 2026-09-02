"use client";

import { TopBar } from "./TopBar";
import { AnimatedPage } from "@/components/motion/AnimatedPage";

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
        <AnimatedPage className="relative px-4 py-5 sm:px-6 lg:px-8">{children}</AnimatedPage>
      </main>
    </>
  );
}
