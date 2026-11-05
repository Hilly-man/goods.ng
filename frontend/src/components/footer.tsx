import Link from "next/link";
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

export function Footer() {
  return (
    <>
    <AfricaSkyline />
    <footer className="bg-brand-950 pb-24 text-white/80 md:pb-0" style={{ backgroundImage: ADIRE_TEXTURE }}>
      <div className="container-page grid gap-8 py-10 md:grid-cols-4 xl:grid-cols-[1.4fr_repeat(4,1fr)]">
        <div className="md:col-span-4 xl:col-span-1">
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
          <div key={c.title}>
            <h3 className="mb-3 text-sm font-semibold text-white">{c.title}</h3>
            <ul className="space-y-2 text-sm">
              {c.links.map(([l, h]) => (
                <li key={h}>
                  <Link href={h} className="hover:text-white">{l}</Link>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>
      <div className="border-t border-white/10">
        <div className="container-page flex flex-col gap-2 py-4 text-xs sm:flex-row sm:items-center sm:justify-between">
          <p>© 2026 Goods.ng. All rights reserved.</p>
          <p className="flex items-center gap-1.5">
            <ShieldCheck className="size-4 text-brand-400" />
            Protected Checkout funds are held by our licensed payment &amp; escrow partner.
          </p>
        </div>
      </div>
    </footer>
    </>
  );
}
