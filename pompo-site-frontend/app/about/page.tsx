import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import { getAboutContent } from "@/lib/api/site";

export const metadata: Metadata = {
  title: "About Us",
  description:
    "POMPO Pay App is a Malawi-focused technology company building digital payment infrastructure.",
  alternates: { canonical: "/about" },
};

export default async function AboutPage() {
  try {
    const data = await getAboutContent();

    return (
      <>
        <section className="border-b border-slate-line py-20 sm:py-28">
          <Container>
            <Reveal className="max-w-2xl">
              <p className="text-sm font-medium text-indigo-500">About Us</p>
              <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
                Payment infrastructure, built for Malawi.
              </h1>
              <p className="mt-6 text-[17px] leading-relaxed text-slate-soft">
                {data.summary}
              </p>
            </Reveal>
          </Container>
        </section>

        <section className="py-20 sm:py-28">
          <Container>
            <Reveal>
              <h2 className="font-display text-2xl font-medium text-ink sm:text-3xl">Founders</h2>
            </Reveal>
            <div className="mt-10 grid grid-cols-1 gap-8 sm:grid-cols-2">
              {data.founders.map((founder, i) => (
                <Reveal key={founder.name} delay={i * 0.08}>
                  <div className="border-t border-slate-line pt-6">
                    <div
                      aria-hidden
                      className="mb-5 h-12 w-12 rounded-full bg-brand-gradient"
                    />
                    <h3 className="font-display text-lg font-medium text-ink">{founder.name}</h3>
                    <p className="mt-1 text-sm text-slate-soft">{founder.role}</p>
                  </div>
                </Reveal>
              ))}
            </div>
          </Container>
        </section>
      </>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load About page content"
        message={err instanceof Error ? err.message : "Failed to retrieve about information from the POMPO API."}
        retryHref="/about"
      />
    );
  }
}
