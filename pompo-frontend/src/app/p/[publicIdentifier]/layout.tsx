import type { Metadata } from "next";
import { PUBLIC_CHECKOUT_ORIGIN } from "@/lib/checkout/publicCheckout";

interface LayoutProps {
  params: Promise<{ publicIdentifier: string }>;
  children: React.ReactNode;
}

export async function generateMetadata({ params }: LayoutProps): Promise<Metadata> {
  const { publicIdentifier } = await params;
  const id = publicIdentifier.replace(/^.*\/p\//, "").replace(/[/?#].*$/, "");
  const url = `${PUBLIC_CHECKOUT_ORIGIN}/p/${encodeURIComponent(id)}`;

  return {
    title: "Pay with POMPO",
    description: "Secure POMPO payment. Confirm the merchant and amount before you pay.",
    alternates: { canonical: url },
    openGraph: {
      title: "Pay with POMPO",
      description: "Secure payment on pay.pompo.mw",
      url,
      siteName: "POMPO",
    },
  };
}

export default function PublicPayIdentifierLayout({ children }: LayoutProps) {
  return children;
}
