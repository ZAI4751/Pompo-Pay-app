import type { Metadata } from "next";
import { Space_Grotesk, Inter } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/layout/Navbar";
import Footer from "@/components/layout/Footer";
import { SITE } from "@/lib/constants";
import { getSiteOverview } from "@/lib/api/site";

const spaceGrotesk = Space_Grotesk({
  subsets: ["latin"],
  weight: ["500", "600", "700"],
  variable: "--font-display",
  display: "swap",
});

const inter = Inter({
  subsets: ["latin"],
  weight: ["400", "500", "600"],
  variable: "--font-body",
  display: "swap",
});

export async function generateMetadata(): Promise<Metadata> {
  try {
    const overview = await getSiteOverview();
    return {
      metadataBase: new URL(SITE.url),
      title: {
        default: overview.seo.title,
        template: `%s | ${SITE.name}`,
      },
      description: overview.seo.description,
      icons: {
        icon: [
          { url: "/icon-32.png", sizes: "32x32", type: "image/png" },
          { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
        ],
        apple: [{ url: "/apple-touch-icon.png", sizes: "180x180", type: "image/png" }],
        shortcut: ["/favicon.ico"],
      },
      openGraph: {
        title: overview.seo.title,
        description: overview.seo.description,
        url: SITE.url,
        siteName: overview.seo.site_name,
        images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "POMPO" }],
        locale: "en_US",
        type: "website",
      },
      twitter: {
        card: "summary_large_image",
        title: overview.seo.title,
        description: overview.seo.description,
        images: ["/og-image.png"],
      },
      robots: {
        index: true,
        follow: true,
      },
      alternates: {
        canonical: "/",
      },
    };
  } catch {
    return {
      metadataBase: new URL(SITE.url),
      title: {
        default: "POMPO | Digital Payment Gateway for Malawi",
        template: "%s | POMPO",
      },
      description: SITE.description,
      robots: {
        index: true,
        follow: true,
      },
      alternates: {
        canonical: "/",
      },
    };
  }
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={`${spaceGrotesk.variable} ${inter.variable}`}>
      <body className="font-body antialiased">
        <a
          href="#main-content"
          className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-[100] focus:rounded-full focus:bg-ink focus:px-4 focus:py-2 focus:text-white"
        >
          Skip to content
        </a>
        <Navbar />
        <main id="main-content">{children}</main>
        <Footer />
      </body>
    </html>
  );
}
