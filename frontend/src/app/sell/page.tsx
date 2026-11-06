import Link from "next/link";
import type { Metadata } from "next";
import { BadgeCheck, BarChart3, Camera, Crown, Handshake, ShieldCheck, Wallet } from "lucide-react";
import { ButtonLink } from "@/components/ui";

export const metadata: Metadata = { title: "Sell on Goods.ng", description: "Post free ads, reach buyers across Nigeria and get paid safely.", alternates: { canonical: "/sell" } };

const BENEFITS = [
  { icon: Camera, title: "Post free ads in minutes", body: "Add photos, set your price and choose delivery options. Listing is always free." },
  { icon: Handshake, title: "Negotiate in-app", body: "Receive offers, counter, and accept. The agreed price goes straight into checkout." },
  { icon: ShieldCheck, title: "Get paid safely", body: "Protected Checkout means no fake alerts — orders are only marked paid after we verify with the payment provider." },
  { icon: Wallet, title: "Sell to more buyers", body: "Offer Goods Flex so buyers can pay in instalments while you're paid in full through escrow." },
  { icon: BadgeCheck, title: "Build trust", body: "Verify your identity or business to earn the Verified badge and rank higher with buyers." },
  { icon: BarChart3, title: "Track performance", body: "See views, enquiries, contact clicks and sales from your seller dashboard." },
];

export default function Page() {
  return (
    <>
      <section className="bg-gradient-to-br from-brand-800 to-brand-950 text-white">
        <div className="container-page py-12 sm:py-16">
          <h1 className="max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl">Sell faster to buyers across Nigeria</h1>
          <p className="mt-3 max-w-xl text-white/85">Free listings, real negotiation, and protected payments that land in your account after delivery.</p>
          <div className="mt-6 flex flex-wrap gap-3">
            <ButtonLink href="/seller/onboarding" variant="accent" size="lg">Start selling — it&apos;s free</ButtonLink>
            <Link href="/premium" className="inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-white/40 px-5 text-base font-semibold text-white transition hover:border-white hover:bg-white/10"><Crown className="size-5" />Go Premium</Link>
          </div>
        </div>
      </section>
      <div className="container-page py-10">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {BENEFITS.map((b) => (
            <div key={b.title} className="card p-5">
              <b.icon className="size-7 text-brand-700" />
              <h2 className="mt-3 font-semibold">{b.title}</h2>
              <p className="mt-1 text-sm text-muted">{b.body}</p>
            </div>
          ))}
        </div>
        <section id="verification" className="card mt-8 p-6">
          <h2 className="text-xl font-bold">Seller verification levels</h2>
          <div className="mt-4 grid gap-3 sm:grid-cols-4">
            {[["Unverified", "New account"], ["Phone verified", "Confirm your number by OTP"], ["Identity verified", "NIN, passport, driver's licence or voter's card reviewed"], ["Business verified", "CAC registration reviewed"]].map(([t, d], i) => (
              <div key={t} className="rounded-xl border border-line p-4">
                <span className="text-xs font-bold text-brand-700">LEVEL {i}</span>
                <p className="mt-1 font-semibold">{t}</p>
                <p className="mt-0.5 text-sm text-muted">{d}</p>
              </div>
            ))}
          </div>
          <p className="mt-3 text-sm text-muted">Verification is separate from Premium. Premium is a paid subscription; verification is earned by proving who you are.</p>
        </section>
        <section className="card mt-6 p-6">
          <h2 className="text-xl font-bold">Fees</h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            <li>• Listing: <strong>free</strong></li>
            <li>• Commission on completed Protected Checkout sales: <strong>5% of item price</strong></li>
            <li>• Direct (off-platform) deals: <strong>no commission</strong> — but no escrow protection</li>
          </ul>
        </section>
      </div>
    </>
  );
}
