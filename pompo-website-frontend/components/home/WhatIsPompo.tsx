import Container from "@/components/ui/Container";
import SectionHeading from "@/components/ui/SectionHeading";
import Reveal from "@/components/ui/Reveal";
import { HomeSection } from "@/lib/types";

interface WhatIsPompoProps {
  sections: HomeSection[];
}

export default function WhatIsPompo({ sections }: WhatIsPompoProps) {
  const displaySections = sections.slice(0, 3);

  return (
    <section className="border-t border-slate-line py-20 sm:py-28">
      <Container>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <SectionHeading
            title="What POMPO is"
            body="A single digital payment gateway connecting the parties in a transaction."
          />
          <div className="grid grid-cols-1 gap-10 sm:grid-cols-3">
            {displaySections.map((section, i) => (
              <Reveal key={section.heading} delay={i * 0.08}>
                <div className="border-t border-slate-line pt-5">
                  <h3 className="font-display text-[17px] font-medium text-ink">{section.heading}</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-slate-soft">{section.body}</p>
                </div>
              </Reveal>
            ))}
          </div>
        </div>
      </Container>
    </section>
  );
}
