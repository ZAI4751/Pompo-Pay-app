import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import SolutionCard from "@/components/solutions/SolutionCard";
import Button from "@/components/ui/Button";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import { getSolutionsContent } from "@/lib/api/site";

export const metadata: Metadata = {
  title: "Solutions",
  description: "POMPO's solutions for merchants, customers, developers, and payment providers.",
  alternates: { canonical: "/solutions" },
};

export default async function SolutionsPage() {
  try {
    const solutions = await getSolutionsContent();

    return (
      <>
        <section className="border-b border-slate-line py-20 sm:py-28">
          <Container>
            <Reveal className="max-w-2xl">
              <p className="text-sm font-medium text-indigo-500">Solutions</p>
              <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
                Built for every side of a transaction.
              </h1>
              <p className="mt-6 text-[17px] leading-relaxed text-slate-soft">
                Merchants, customers, developers, and payment providers each need something
                different from POMPO. Here&apos;s what each side gets.
              </p>
            </Reveal>
          </Container>
        </section>

        <section className="py-20 sm:py-28">
          <Container>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2">
              {solutions.map((s, i) => (
                <SolutionCard key={s.name} title={s.name} body={s.description} index={i} />
              ))}
            </div>
          </Container>
        </section>

        <section className="border-t border-slate-line bg-mist py-20 sm:py-28">
          <Container className="max-w-2xl text-center">
            <Reveal>
              <h2 className="font-display text-2xl font-medium text-ink sm:text-3xl">
                Building or integrating a business?
              </h2>
              <p className="mx-auto mt-3 max-w-md text-[15px] leading-relaxed text-slate-soft">
                Tell us about what you&apos;re building and we&apos;ll follow up.
              </p>
              <div className="mt-8 flex justify-center">
                <Button href="/contact" variant="primary">
                  Get in Touch
                </Button>
              </div>
            </Reveal>
          </Container>
        </section>
      </>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load Solutions content"
        message={err instanceof Error ? err.message : "Failed to retrieve solutions data from the POMPO API."}
        retryHref="/solutions"
      />
    );
  }
}
