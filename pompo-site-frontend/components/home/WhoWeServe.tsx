import Container from "@/components/ui/Container";
import SectionHeading from "@/components/ui/SectionHeading";
import Reveal from "@/components/ui/Reveal";

const AUDIENCES = [
  {
    title: "Merchants",
    body: "Businesses that want a single way to accept payments and see them clearly, without juggling separate provider systems.",
  },
  {
    title: "Customers",
    body: "People paying merchants through the payment methods POMPO supports, with a simple checkout experience.",
  },
  {
    title: "Developers & POS teams",
    body: "Teams integrating payment acceptance into their own software through POMPO's API.",
  },
];

export default function WhoWeServe() {
  return (
    <section className="border-t border-slate-line py-20 sm:py-28">
      <Container>
        <SectionHeading
          align="center"
          title="Who POMPO serves"
          body="Three groups, one connected payment experience."
        />
        <div className="mx-auto mt-14 grid max-w-4xl grid-cols-1 gap-8 sm:grid-cols-3">
          {AUDIENCES.map((a, i) => (
            <Reveal key={a.title} delay={i * 0.08}>
              <div className="h-full rounded-2xl border border-slate-line p-7 transition-colors hover:border-indigo-400/60">
                <h3 className="font-display text-lg font-medium text-ink">{a.title}</h3>
                <p className="mt-2.5 text-[15px] leading-relaxed text-slate-soft">{a.body}</p>
              </div>
            </Reveal>
          ))}
        </div>
      </Container>
    </section>
  );
}
