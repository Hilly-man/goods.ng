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

const SITE = process.env.NEXT_PUBLIC_SITE_URL ?? "http://localhost:3000";

export const metadata: Metadata = {
  metadataBase: new URL(SITE),
  title: { default: "Goods.ng — Buy. Sell. Trade with Confidence.", template: "%s | Goods.ng" },
  description:
    "Nigeria's marketplace for phones, cars, electronics, fashion, property and more. Chat and negotiate with sellers, pay with escrow-protected checkout, or spread payments with Goods Flex.",
  applicationName: "Goods.ng",
  openGraph: { type: "website", siteName: "Goods.ng", locale: "en_NG" },
  twitter: { card: "summary_large_image" },
  formatDetection: { telephone: false },
};

export const viewport: Viewport = {
  themeColor: "#08603b",
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
