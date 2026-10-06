import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import { ABOUT_SUMMARY } from "@/lib/content";

export const metadata: Metadata = {
  title: "About Us",
  description:
    "POMPO Pay App is a Malawi-focused technology company building digital payment infrastructure.",
  alternates: { canonical: "/about" },
};

export default function AboutPage() {
  return (
    <section className="border-b border-slate-line py-20 sm:py-28">
      <Container>
        <Reveal className="max-w-2xl">
          <p className="text-sm font-medium text-indigo-500">About Us</p>
          <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
            Payment infrastructure, built for Malawi.
          </h1>
          <p className="mt-6 text-[17px] leading-relaxed text-slate-soft">{ABOUT_SUMMARY}</p>
        </Reveal>
      </Container>
    </section>
  );
}
