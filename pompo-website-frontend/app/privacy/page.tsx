import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import { CONTACT } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Privacy Policy",
  description: "How POMPO handles information collected through this website.",
  alternates: { canonical: "/privacy" },
  robots: { index: true, follow: true },
};

export default function PrivacyPage() {
  return (
    <section className="py-20 sm:py-28">
      <Container className="max-w-2xl">
        <p className="text-sm font-medium text-indigo-500">Legal</p>
        <h1 className="mt-4 font-display text-4xl font-medium leading-[1.15] text-ink">
          Privacy Policy
        </h1>
        <p className="mt-4 text-sm text-slate-soft">Last updated: {new Date().getFullYear()}</p>

        <div className="prose-sm mt-12 space-y-8 text-[15px] leading-relaxed text-slate-soft">
          <div>
            <h2 className="font-display text-lg font-medium text-ink">Information we collect</h2>
            <p className="mt-2">
              This website collects the information you choose to submit through the contact
              form, such as your name, email address, phone number, company, and message. We do
              not collect this information through any other means on this website.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">How we use it</h2>
            <p className="mt-2">
              We use the information you submit only to respond to your enquiry and to
              communicate with you about it. We do not sell your information to third parties.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Payment information</h2>
            <p className="mt-2">
              This website is an informational site about POMPO and does not process payments
              itself. Any payment processing is handled by POMPO&apos;s underlying platform and
              its supported payment providers, subject to their own applicable terms.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Data retention</h2>
            <p className="mt-2">
              We retain contact form submissions for as long as reasonably needed to respond to
              and resolve your enquiry.
            </p>
          </div>

          <div>
            <h2 className="font-display text-lg font-medium text-ink">Contact us</h2>
            <p className="mt-2">
              If you have questions about this policy or want your information removed, contact
              us at{" "}
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
