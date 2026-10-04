import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import { getGoalsContent } from "@/lib/api/site";

export const metadata: Metadata = {
  title: "Goals",
  description: "POMPO's current goals as it builds out its payment infrastructure.",
  alternates: { canonical: "/goals" },
};

export default async function GoalsPage() {
  try {
    const data = await getGoalsContent();

    return (
      <section className="py-20 sm:py-28">
        <Container className="max-w-3xl">
          <Reveal>
            <p className="text-sm font-medium text-indigo-500">Current Goals</p>
            <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
              Where we&apos;re focused right now.
            </h1>
            <p className="mt-6 max-w-xl text-[17px] leading-relaxed text-slate-soft">
              These are goals POMPO is actively working toward, not milestones we&apos;ve already
              reached.
            </p>
          </Reveal>

          <ul className="mt-14 space-y-6">
            {data.goals.map((goal, i) => (
              <Reveal key={goal} delay={i * 0.05}>
                <li className="flex gap-5 border-t border-slate-line pt-6 text-[16px] leading-relaxed text-ink">
                  <span
                    aria-hidden
                    className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-brand-gradient"
                  />
                  {goal}
                </li>
              </Reveal>
            ))}
          </ul>
        </Container>
      </section>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load Goals content"
        message={err instanceof Error ? err.message : "Failed to retrieve current goals from the POMPO API."}
        retryHref="/goals"
      />
    );
  }
}
