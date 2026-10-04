import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import FaqAccordion from "@/components/faq/FaqAccordion";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import { getFaqContent } from "@/lib/api/site";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Answers to common questions about POMPO's digital payment gateway.",
  alternates: { canonical: "/faq" },
};

export default async function FaqPage() {
  try {
    const items = await getFaqContent();

    return (
      <section className="py-20 sm:py-28">
        <Container className="max-w-3xl">
          <Reveal>
            <p className="text-sm font-medium text-indigo-500">FAQ</p>
            <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
              Common questions.
            </h1>
          </Reveal>
          <div className="mt-12">
            <FaqAccordion items={items} />
          </div>
        </Container>
      </section>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load FAQ content"
        message={err instanceof Error ? err.message : "Failed to retrieve FAQ items from the POMPO API."}
        retryHref="/faq"
      />
    );
  }
}
