import Reveal from "./Reveal";

export default function SectionHeading({
  title,
  body,
  align = "left",
}: {
  title: string;
  body?: string;
  align?: "left" | "center";
}) {
  return (
    <Reveal className={align === "center" ? "text-center" : ""}>
      <h2
        className={`font-display text-balance text-3xl font-medium leading-[1.15] text-ink sm:text-4xl ${
          align === "center" ? "mx-auto max-w-2xl" : "max-w-xl"
        }`}
      >
        {title}
      </h2>
      {body && (
        <p
          className={`mt-4 text-[17px] leading-relaxed text-slate-soft ${
            align === "center" ? "mx-auto max-w-xl" : "max-w-md"
          }`}
        >
          {body}
        </p>
      )}
    </Reveal>
  );
}
