import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import { MISSION, VISION } from "@/lib/content";

export const metadata: Metadata = {
  title: "Vision & Mission",
  description: "POMPO's vision and mission for digital payments in Malawi.",
  alternates: { canonical: "/vision-mission" },
};

export default function VisionMissionPage() {
  return (
    <>
        <section className="border-b border-slate-line bg-ink py-24 sm:py-32">
          <Container>
            <Reveal className="max-w-2xl">
              <p className="text-sm font-medium text-indigo-400">Vision</p>
              <p className="mt-5 font-display text-3xl font-medium leading-snug text-white sm:text-4xl">
                {VISION}
              </p>
            </Reveal>
          </Container>
        </section>

        <section className="py-24 sm:py-32">
          <Container>
            <Reveal className="max-w-2xl">
              <p className="text-sm font-medium text-violet-500">Mission</p>
              <p className="mt-5 font-display text-3xl font-medium leading-snug text-ink sm:text-4xl">
                {MISSION}
              </p>
            </Reveal>
          </Container>
        </section>
    </>
  );
}
