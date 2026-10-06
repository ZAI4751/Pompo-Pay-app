import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import FaqAccordion from "@/components/faq/FaqAccordion";
import { FAQ_ITEMS } from "@/lib/content";

export const metadata: Metadata = {
  title: "FAQ",
  description: "Answers to common questions about POMPO's digital payment gateway.",
  alternates: { canonical: "/faq" },
};

export default function FaqPage() {
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
          <FaqAccordion items={FAQ_ITEMS} />
        </div>
      </Container>
    </section>
  );
}
