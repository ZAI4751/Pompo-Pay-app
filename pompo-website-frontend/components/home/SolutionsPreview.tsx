import Container from "@/components/ui/Container";
import SectionHeading from "@/components/ui/SectionHeading";
import Button from "@/components/ui/Button";
import SolutionCard from "@/components/solutions/SolutionCard";
import { SolutionItem } from "@/lib/types";

interface SolutionsPreviewProps {
  solutions: SolutionItem[];
}

export default function SolutionsPreview({ solutions }: SolutionsPreviewProps) {
  return (
    <section className="border-t border-slate-line bg-mist py-20 sm:py-28">
      <Container>
        <div className="flex flex-col items-start justify-between gap-6 sm:flex-row sm:items-end">
          <SectionHeading title="Solutions" body="Built around every side of a transaction." />
          <Button href="/solutions" variant="ghost">
            View all solutions
          </Button>
        </div>
        <div className="mt-12 grid grid-cols-1 gap-6 sm:grid-cols-2">
          {solutions.map((s, i) => (
            <SolutionCard key={s.name} title={s.name} body={s.description} index={i} />
          ))}
        </div>
      </Container>
    </section>
  );
}
