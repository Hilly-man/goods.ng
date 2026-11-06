import Link from "next/link";
import { CookieSettingsLink } from "./consent";
import { AppBadges } from "./app-badges";
import { Mail, Phone, ShieldCheck } from "lucide-react";
import { Logo } from "./logo";
import { ADIRE_TEXTURE, AfricaSkyline } from "./africa-skyline";
import { SocialLinks } from "./social-links";

const COLS = [
  {
    title: "Goods.ng",
    links: [
      ["About us", "/about"],
      ["How it works", "/how-it-works"],
      ["Contact us", "/contact"],
      ["FAQ", "/faq"],
    ],
  },
  {
    title: "Buying",
    links: [
      ["Buyer Protection", "/buyer-protection"],
      ["Goods Flex (pay later)", "/flex/about"],
      ["Refund & dispute policy", "/refund-policy"],
      ["Safety tips", "/buyer-protection#safety"],
    ],
  },
  {
    title: "Selling",
    links: [
      ["Sell on Goods.ng", "/sell"],
      ["Premium Seller", "/premium"],
      ["Seller verification", "/sell#verification"],
      ["Seller dashboard", "/seller"],
    ],
  },
  {
    title: "Legal",
    links: [
      ["Terms & conditions", "/terms"],
      ["Privacy policy", "/privacy"],
    ],
  },
];

/** The handful of links people actually need on a phone. */
const MOBILE_LINKS = [
  ["About", "/about"],
  ["Contact", "/contact"],
  ["FAQ", "/faq"],
  ["Buyer Protection", "/buyer-protection"],
  ["Sell", "/sell"],
  ["Terms", "/terms"],
  ["Privacy", "/privacy"],
];

export function Footer() {
  return (
    <div className="site-footer">
      <AfricaSkyline />
      <footer className="bg-brand-950 pb-24 text-white/80 md:pb-0" style={{ backgroundImage: ADIRE_TEXTURE }}>
        {/* Phones: short and simple */}
        <div className="container-page space-y-6 py-8 md:hidden">
          <div className="flex flex-col items-center gap-2 text-center">
            <Logo light />
            <p className="text-sm">Buy. Sell. Trade with Confidence.</p>
          </div>
          <div className="flex justify-center"><SocialLinks /></div>
          <nav aria-label="Footer" className="flex flex-wrap justify-center gap-x-4 gap-y-2 text-sm">
            {MOBILE_LINKS.map(([l, h]) => <Link key={h} href={h} className="hover:text-white">{l}</Link>)}
          </nav>
          <div className="flex justify-center"><AppBadges compact /></div>
          <p className="border-t border-white/10 pt-4 text-center text-xs text-white/60">© 2026 Goods.ng · Payments protected by our licensed escrow partner. · <CookieSettingsLink className="underline hover:text-white" /></p>
        </div>

        {/* Tablet & desktop: full footer */}
        <div className="hidden md:block">
          <div className="container-page grid gap-8 py-10 md:grid-cols-3 lg:grid-cols-[repeat(3,1fr)_1.6fr] xl:grid-cols-[1.45fr_repeat(3,0.9fr)_1.4fr]">
            <div className="md:col-span-3 lg:col-span-4 xl:col-span-1">
              <Logo light />
              <p className="mt-3 max-w-xs text-sm">Buy. Sell. Trade with Confidence. Nigeria&apos;s marketplace with escrow-protected checkout and flexible payments.</p>
              <div className="mt-4 space-y-1.5 text-sm">
                <a href="mailto:support@goods.ng" className="flex items-center gap-2 hover:text-white"><Mail className="size-4" /> support@goods.ng</a>
                <a href="tel:+2342013300000" className="flex items-center gap-2 hover:text-white"><Phone className="size-4" /> +234 201 330 0000</a>
              </div>
              <div className="mt-5">
                <SocialLinks />
              </div>
            </div>
            {COLS.map((c) => (
              <div key={c.title} className={c.title === "Legal" ? "md:col-span-3 lg:col-span-1" : undefined}>
                <h3 className="mb-3 text-sm font-semibold text-white">{c.title}</h3>
                <ul className="space-y-2 text-sm">
                  {c.links.map(([l, h]) => (
                    <li key={h}>
                      <Link href={h} className="hover:text-white">{l}</Link>
                    </li>
                  ))}
                </ul>
                {c.title === "Legal" && (
                  <div className="mt-6">
                    <AppBadges />
                  </div>
                )}
              </div>
            ))}
          </div>
          <div className="border-t border-white/10">
            <div className="container-page flex flex-col gap-2 py-4 text-xs sm:flex-row sm:items-center sm:justify-between">
              <p>© 2026 Goods.ng. All rights reserved. · <CookieSettingsLink className="underline hover:text-white" /></p>
              <p className="flex items-center gap-1.5">
                <ShieldCheck className="size-4 text-brand-400" />
                Protected Checkout funds are held by our licensed payment &amp; escrow partner.
              </p>
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
}
