import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";

interface VisionMissionPreviewProps {
  vision: string;
  mission: string;
}

export default function VisionMissionPreview({
  vision,
  mission,
}: VisionMissionPreviewProps) {
  return (
    <section className="border-t border-slate-line bg-ink py-24 sm:py-32">
      <Container>
        <div className="grid grid-cols-1 gap-14 lg:grid-cols-2 lg:gap-20">
          <Reveal>
            <p className="text-sm font-medium text-indigo-400">Vision</p>
            <p className="mt-4 max-w-lg font-display text-2xl font-medium leading-snug text-white sm:text-[1.75rem]">
              {vision}
            </p>
          </Reveal>
          <Reveal delay={0.1}>
            <p className="text-sm font-medium text-violet-400">Mission</p>
            <p className="mt-4 max-w-lg font-display text-2xl font-medium leading-snug text-white sm:text-[1.75rem]">
              {mission}
            </p>
          </Reveal>
        </div>
      </Container>
    </section>
  );
}
