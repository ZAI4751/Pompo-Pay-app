import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import FlowDiagram from "@/components/how-it-works/FlowDiagram";
import PaymentNetworkVisual from "@/components/home/PaymentNetworkVisual";
import ApiErrorNotice from "@/components/ui/ApiErrorNotice";
import { getHowItWorksContent } from "@/lib/api/site";

export const metadata: Metadata = {
  title: "How POMPO Works",
  description: "How a payment moves from customer to merchant through the POMPO gateway.",
  alternates: { canonical: "/how-it-works" },
};

export default async function HowItWorksPage() {
  try {
    const data = await getHowItWorksContent();

    return (
      <>
        <section className="border-b border-slate-line py-20 sm:py-28">
          <Container>
            <div className="grid grid-cols-1 items-center gap-14 lg:grid-cols-2 lg:gap-10">
              <Reveal>
                <p className="text-sm font-medium text-indigo-500">How It Works</p>
                <h1 className="mt-4 max-w-lg font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
                  A payment gateway, not a wallet.
                </h1>
                <p className="mt-6 max-w-md text-[17px] leading-relaxed text-slate-soft">
                  {data.clarification}
                </p>
                {data.flow && data.flow.length > 0 && (
                  <div className="mt-8 flex flex-wrap items-center gap-2">
                    {data.flow.map((node, i) => (
                      <span key={node} className="inline-flex items-center gap-2">
                        <span className="rounded-full border border-slate-line bg-mist px-3 py-1 text-xs font-medium text-ink">
                          {node}
                        </span>
                        {i < data.flow.length - 1 && (
                          <span className="text-slate-400 text-xs">→</span>
                        )}
                      </span>
                    ))}
                  </div>
                )}
              </Reveal>
              <div className="mx-auto aspect-[13/10] w-full max-w-md">
                <PaymentNetworkVisual />
              </div>
            </div>
          </Container>
        </section>

        <section className="py-20 sm:py-28">
          <Container className="max-w-3xl">
            <Reveal>
              <h2 className="font-display text-2xl font-medium text-ink sm:text-3xl">
                The steps of a transaction
              </h2>
            </Reveal>
            <div className="mt-12">
              <FlowDiagram steps={data.steps} />
            </div>
          </Container>
        </section>

        <section className="border-t border-slate-line bg-mist py-20 sm:py-28">
          <Container className="max-w-3xl">
            <Reveal>
              <h2 className="font-display text-2xl font-medium text-ink sm:text-3xl">
                What POMPO is — and isn&apos;t
              </h2>
              <div className="mt-8 grid grid-cols-1 gap-6 sm:grid-cols-2">
                <div className="rounded-2xl border border-slate-line bg-white p-7">
                  <h3 className="font-display text-base font-medium text-ink">POMPO is</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-slate-soft">
                    A digital payment gateway that routes transactions between customers,
                    merchants, and supported payment providers.
                  </p>
                </div>
                <div className="rounded-2xl border border-slate-line bg-white p-7">
                  <h3 className="font-display text-base font-medium text-ink">POMPO isn&apos;t</h3>
                  <p className="mt-2 text-[15px] leading-relaxed text-slate-soft">
                    {data.clarification}
                  </p>
                </div>
              </div>
            </Reveal>
          </Container>
        </section>
      </>
    );
  } catch (err) {
    return (
      <ApiErrorNotice
        title="Could not load How It Works content"
        message={err instanceof Error ? err.message : "Failed to retrieve How It Works data from the POMPO API."}
        retryHref="/how-it-works"
      />
    );
  }
}
