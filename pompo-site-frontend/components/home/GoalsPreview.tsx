import Container from "@/components/ui/Container";
import SectionHeading from "@/components/ui/SectionHeading";
import Button from "@/components/ui/Button";
import Reveal from "@/components/ui/Reveal";

interface GoalsPreviewProps {
  goals: string[];
}

export default function GoalsPreview({ goals }: GoalsPreviewProps) {
  const preview = goals.slice(0, 4);

  return (
    <section className="border-t border-slate-line py-20 sm:py-28">
      <Container>
        <div className="grid grid-cols-1 gap-12 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <div>
            <SectionHeading
              title="Where we're focused now"
              body="Current goals POMPO is actively working toward — not finished milestones."
            />
            <div className="mt-8">
              <Button href="/goals" variant="ghost">
                See all current goals
              </Button>
            </div>
          </div>
          <ul className="space-y-5">
            {preview.map((goal, i) => (
              <Reveal key={goal} delay={i * 0.06}>
                <li className="flex gap-4 border-t border-slate-line pt-5 text-[15px] leading-relaxed text-ink">
                  <span aria-hidden className="mt-2 h-1.5 w-1.5 flex-none rounded-full bg-brand-gradient" />
                  {goal}
                </li>
              </Reveal>
            ))}
          </ul>
        </div>
      </Container>
    </section>
  );
}
