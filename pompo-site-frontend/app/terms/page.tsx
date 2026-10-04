import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import { CONTACT } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Terms of Service",
  description: "Terms for using the POMPO website.",
  alternates: { canonical: "/terms" },
  robots: { index: true, follow: true },
};

export default function TermsPage() {
  return (
    <section className="py-20 sm:py-28">
      <Container className="max-w-2xl">
        <p className="text-sm font-medium text-indigo-500">Legal</p>
        <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink">
          Terms of Service
        </h1>
        <p className="mt-4 text-sm text-slate-soft">Last updated: {new Date().getFullYear()}</p>

        <div className="prose-sm mt-12 space-y-8 text-[15px] leading-relaxed text-slate-soft">
          <div>
            <h2 className="font-display text-lg font-medium text-ink">About this website</h2>
            <p className="mt-2">
              This website is the informational, public-facing website for POMPO Pay App. It
              describes who POMPO is, what POMPO does, and how to get in touch. It does not
              itself process payments or hold funds.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Use of this website</h2>
            <p className="mt-2">
              You may browse this website and use the contact form to reach POMPO. You agree not
              to misuse this website, including attempting to disrupt it or submit false or
              malicious information through the contact form.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Accuracy of information</h2>
            <p className="mt-2">
              We aim to keep the information on this website accurate and up to date. Details
              about POMPO&apos;s products, goals, and supported payment providers may change as
              POMPO develops.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Intellectual property</h2>
            <p className="mt-2">
              The POMPO name, logo, and content on this website belong to POMPO Pay App and may
              not be used without permission.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Contact</h2>
            <p className="mt-2">
              Questions about these terms can be sent to{" "}
              <a href={`mailto:${CONTACT.email}`} className="text-ink underline underline-offset-2">
                {CONTACT.email}
              </a>
              .
            </p>
          </div>
        </div>
      </Container>
    </section>
  );
}
