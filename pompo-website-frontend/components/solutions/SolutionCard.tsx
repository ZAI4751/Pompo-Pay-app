import Reveal from "@/components/ui/Reveal";

export default function SolutionCard({
  title,
  body,
  index,
}: {
  title: string;
  body: string;
  index: number;
}) {
  return (
    <Reveal delay={index * 0.07}>
      <div className="group relative overflow-hidden rounded-2xl border border-slate-line bg-white p-8 transition-all duration-300 hover:-translate-y-1 hover:border-transparent hover:shadow-[0_20px_50px_-20px_rgba(67,56,245,0.25)]">
        <div
          aria-hidden
          className="absolute inset-x-0 top-0 h-1 origin-left scale-x-0 bg-brand-gradient transition-transform duration-300 group-hover:scale-x-100"
        />
        <h3 className="font-display text-xl font-medium text-ink">{title}</h3>
        <p className="mt-3 text-[15px] leading-relaxed text-slate-soft">{body}</p>
      </div>
    </Reveal>
  );
}
