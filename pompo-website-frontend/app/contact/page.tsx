import type { Metadata } from "next";
import Container from "@/components/ui/Container";
import Reveal from "@/components/ui/Reveal";
import ContactForm from "@/components/contact/ContactForm";
import { CONTACT } from "@/lib/constants";

export const metadata: Metadata = {
  title: "Contact Us",
  description: "Get in touch with the POMPO team.",
  alternates: { canonical: "/contact" },
};

export default function ContactPage() {
  return (
    <section className="py-20 sm:py-28">
      <Container>
        <div className="grid grid-cols-1 gap-16 lg:grid-cols-[0.8fr_1.2fr] lg:gap-20">
          <Reveal>
            <p className="text-sm font-medium text-indigo-500">Contact Us</p>
            <h1 className="mt-4 max-w-sm font-display text-4xl font-medium leading-[1.15] text-ink sm:text-5xl">
              Get in touch.
            </h1>
            <p className="mt-6 max-w-sm text-[17px] leading-relaxed text-slate-soft">
              Have a question, a partnership idea, or something to build together? Send us a
              message, or reach out directly.
            </p>

            <dl className="mt-10 space-y-5 border-t border-slate-line pt-8">
              <div>
                <dt className="text-sm text-slate-soft">Email</dt>
                <dd className="mt-1">
                  <a
                    href={`mailto:${CONTACT.email}`}
                    className="text-[16px] font-medium text-ink hover:text-indigo-500"
                  >
                    {CONTACT.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-soft">Phone</dt>
                <dd className="mt-1 space-y-1">
                  {CONTACT.phones.map((phone) => (
                    <div key={phone}>
                      <a
                        href={`tel:${phone.replace(/\s+/g, "")}`}
                        className="text-[16px] font-medium text-ink hover:text-indigo-500"
                      >
                        {phone}
                      </a>
                    </div>
                  ))}
                </dd>
              </div>
              <div>
                <dt className="text-sm text-slate-soft">Country</dt>
                <dd className="mt-1 text-[16px] font-medium text-ink">{CONTACT.country}</dd>
              </div>
            </dl>
          </Reveal>

          <Reveal delay={0.1}>
            <div className="rounded-3xl border border-slate-line p-6 sm:p-10">
              <ContactForm />
            </div>
          </Reveal>
        </div>
      </Container>
    </section>
  );
}
