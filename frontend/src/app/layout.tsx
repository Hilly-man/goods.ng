import type { Metadata, Viewport } from "next";
import { ConsentBanner, TrackingScripts } from "@/components/consent";
import { Suspense } from "react";
import "./globals.css";
import { AuthProvider } from "@/components/auth-provider";
import { ToastProvider } from "@/components/ui";
import { Header } from "@/components/header";
import { MobileNav } from "@/components/mobile-nav";
import { Footer } from "@/components/footer";
import { Logo } from "@/components/logo";
import { InterestCapture } from "@/components/recommended";
import {
  DEFAULT_DESCRIPTION,
  DEFAULT_KEYWORDS,
  DEFAULT_OG_IMAGE,
  FACEBOOK_APP_ID,
  SITE_NAME,
  SITE_URL,
  TWITTER_HANDLE,
} from "@/lib/seo";

const otherVerification: Record<string, string> = {};
if (process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION) {
  otherVerification["msvalidate.01"] = process.env.NEXT_PUBLIC_BING_SITE_VERIFICATION;
}
if (process.env.NEXT_PUBLIC_META_DOMAIN_VERIFICATION) {
  otherVerification["facebook-domain-verification"] = process.env.NEXT_PUBLIC_META_DOMAIN_VERIFICATION;
}

const twitter: Metadata["twitter"] = {
  card: "summary_large_image",
  title: "Goods.ng — Buy. Sell. Trade with Confidence.",
  description: DEFAULT_DESCRIPTION,
  images: [DEFAULT_OG_IMAGE],
};
if (TWITTER_HANDLE) {
  twitter.site = TWITTER_HANDLE;
  twitter.creator = TWITTER_HANDLE;
}

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: { default: "Goods.ng — Buy. Sell. Trade with Confidence.", template: "%s | Goods.ng" },
  description: DEFAULT_DESCRIPTION,
  applicationName: SITE_NAME,
  keywords: DEFAULT_KEYWORDS,
  authors: [{ name: SITE_NAME, url: SITE_URL }],
  creator: SITE_NAME,
  publisher: SITE_NAME,
  category: "Shopping",
  alternates: { canonical: "/" },
  robots: {
    index: true,
    follow: true,
    googleBot: {
      index: true,
      follow: true,
      "max-image-preview": "large",
      "max-snippet": -1,
      "max-video-preview": -1,
    },
  },
  openGraph: {
    type: "website",
    url: SITE_URL,
    siteName: SITE_NAME,
    locale: "en_NG",
    title: "Goods.ng — Buy. Sell. Trade with Confidence.",
    description: DEFAULT_DESCRIPTION,
    images: [{ url: DEFAULT_OG_IMAGE, width: 1200, height: 630, alt: "Goods.ng — Buy. Sell. Trade with Confidence." }],
  },
  twitter,
  icons: {
    icon: [
      { url: "/favicon.ico", sizes: "any", type: "image/x-icon" },
      { url: "/icon.svg", type: "image/svg+xml" },
      { url: "/icon-192.png", sizes: "192x192", type: "image/png" },
    ],
    shortcut: "/favicon.ico",
    apple: [{ url: "/apple-icon.png", sizes: "180x180", type: "image/png" }],
  },
  manifest: "/manifest.webmanifest",
  appleWebApp: { capable: true, title: SITE_NAME, statusBarStyle: "black-translucent" },
  formatDetection: { telephone: false, email: false, address: false },
  verification: {
    ...(process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION
      ? { google: process.env.NEXT_PUBLIC_GOOGLE_SITE_VERIFICATION }
      : {}),
    ...(Object.keys(otherVerification).length ? { other: otherVerification } : {}),
  },
  other: FACEBOOK_APP_ID ? { "fb:app_id": FACEBOOK_APP_ID } : undefined,
};

const organizationJsonLd = {
  "@context": "https://schema.org",
  "@type": "Organization",
  name: SITE_NAME,
  url: SITE_URL,
  logo: `${SITE_URL}/favicon.ico`,
  description: DEFAULT_DESCRIPTION,
  areaServed: { "@type": "Country", name: "Nigeria" },
  contactPoint: {
    "@type": "ContactPoint",
    contactType: "customer support",
    email: "support@goods.ng",
    areaServed: "NG",
    availableLanguage: ["en"],
  },
};

const websiteJsonLd = {
  "@context": "https://schema.org",
  "@type": "WebSite",
  name: SITE_NAME,
  url: SITE_URL,
  description: DEFAULT_DESCRIPTION,
  inLanguage: "en-NG",
  potentialAction: {
    "@type": "SearchAction",
    target: { "@type": "EntryPoint", urlTemplate: `${SITE_URL}/search?q={search_term_string}` },
    "query-input": "required name=search_term_string",
  },
};

export const viewport: Viewport = {
  themeColor: "#18251D",
  width: "device-width",
  initialScale: 1,
};

function HeaderFallback() {
  return (
    <header className="sticky top-0 z-40 bg-brand-800 shadow-md">
      <div className="container-page flex h-14 items-center md:h-16">
        <Logo light />
      </div>
    </header>
  );
}

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en-NG">
      <body className="flex min-h-dvh flex-col">
        <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:z-50 focus:bg-white focus:p-2">
          Skip to content
        </a>
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(organizationJsonLd).replace(/</g, "\\u003c") }}
        />
        <script
          type="application/ld+json"
          dangerouslySetInnerHTML={{ __html: JSON.stringify(websiteJsonLd).replace(/</g, "\\u003c") }}
        />
        <AuthProvider>
          <ToastProvider>
            <Suspense fallback={<HeaderFallback />}>
              <Header />
            </Suspense>
            <main id="main" className="flex-1">
              {children}
            </main>
            <Footer />
            <InterestCapture />
            <Suspense>
              <ConsentBanner />
              <TrackingScripts />
            </Suspense>
            <Suspense>
              <MobileNav />
            </Suspense>
          </ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
