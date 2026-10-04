import Container from "@/components/ui/Container";
import SectionHeading from "@/components/ui/SectionHeading";
import Button from "@/components/ui/Button";
import FlowDiagram from "@/components/how-it-works/FlowDiagram";

interface HowItWorksPreviewProps {
  steps: string[];
}

export default function HowItWorksPreview({ steps }: HowItWorksPreviewProps) {
  return (
    <section className="border-t border-slate-line bg-mist py-20 sm:py-28">
      <Container>
        <div className="grid grid-cols-1 gap-14 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <div>
            <SectionHeading
              title="How POMPO works"
              body="One payment, moved through the right pathway — from customer to merchant."
            />
            <div className="mt-8">
              <Button href="/how-it-works" variant="ghost">
                See the full breakdown
              </Button>
            </div>
          </div>
          <FlowDiagram steps={steps} compact />
        </div>
      </Container>
    </section>
  );
}
