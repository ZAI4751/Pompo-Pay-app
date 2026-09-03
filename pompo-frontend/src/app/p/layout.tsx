import type { Metadata } from "next";
import { PUBLIC_CHECKOUT_ORIGIN } from "@/lib/checkout/publicCheckout";

export const metadata: Metadata = {
  title: {
    default: "Pay with POMPO",
    template: "%s",
  },
  description: "Secure POMPO payment. Confirm the merchant and amount before you pay.",
  applicationName: "POMPO",
  robots: { index: false, follow: false },
  metadataBase: new URL(PUBLIC_CHECKOUT_ORIGIN),
  openGraph: {
    title: "Pay with POMPO",
    description: "Secure payment on pay.pompo.mw",
    siteName: "POMPO",
    type: "website",
  },
  twitter: {
    card: "summary",
    title: "Pay with POMPO",
    description: "Secure payment on pay.pompo.mw",
  },
};

export default function PublicPayLayout({ children }: { children: React.ReactNode }) {
  return children;
}
