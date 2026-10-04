import Image from "next/image";
import Link from "next/link";
import Container from "@/components/ui/Container";
import { CONTACT, FOOTER_LINKS } from "@/lib/constants";

export default function Footer() {
  const year = new Date().getFullYear();

  return (
    <footer className="border-t border-slate-line bg-white">
      <Container className="py-16">
        <div className="grid grid-cols-1 gap-12 md:grid-cols-[1.4fr_1fr_1fr_1fr]">
          <div>
            <div className="flex items-center gap-2.5">
              <Image src="/pompo-mark.png" alt="POMPO" width={110} height={82} className="h-7 w-auto" />
              <span className="font-display text-base font-medium text-ink">POMPO</span>
            </div>
            <p className="mt-4 max-w-xs text-sm leading-relaxed text-slate-soft">
              POMPO Pay App — a digital payment gateway connecting merchants, customers, and
              payment providers in Malawi.
            </p>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink">Company</h3>
            <ul className="mt-4 space-y-3">
              {FOOTER_LINKS.company.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-slate-soft hover:text-ink">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink">Product</h3>
            <ul className="mt-4 space-y-3">
              {FOOTER_LINKS.product.map((l) => (
                <li key={l.href}>
                  <Link href={l.href} className="text-sm text-slate-soft hover:text-ink">
                    {l.label}
                  </Link>
                </li>
              ))}
            </ul>
          </div>

          <div>
            <h3 className="text-sm font-medium text-ink">Contact</h3>
            <ul className="mt-4 space-y-3 text-sm text-slate-soft">
              <li>
                <a href={`mailto:${CONTACT.email}`} className="hover:text-ink">
                  {CONTACT.email}
                </a>
              </li>
              {CONTACT.phones.map((phone) => (
                <li key={phone}>
                  <a href={`tel:${phone.replace(/\s+/g, "")}`} className="hover:text-ink">
                    {phone}
                  </a>
                </li>
              ))}
              <li>{CONTACT.country}</li>
            </ul>
          </div>
        </div>

        <div className="mt-14 flex flex-col-reverse items-start justify-between gap-4 border-t border-slate-line pt-8 sm:flex-row sm:items-center">
          <p className="text-sm text-slate-soft">© {year} POMPO Pay App. All rights reserved.</p>
          <div className="flex gap-6">
            {FOOTER_LINKS.legal.map((l) => (
              <Link key={l.href} href={l.href} className="text-sm text-slate-soft hover:text-ink">
                {l.label}
              </Link>
            ))}
          </div>
        </div>
      </Container>
    </footer>
  );
}
