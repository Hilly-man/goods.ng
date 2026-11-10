import Link from "next/link";
import type { Metadata } from "next";
import { BadgeCheck, BarChart3, Camera, Crown, Handshake, ShieldCheck, Wallet } from "lucide-react";
import { ButtonLink } from "@/components/ui";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "Sell on Goods.ng",
  description:
    "Post free ads, reach buyers across Nigeria, negotiate in-app and get paid safely through Protected Checkout.",
  path: "/sell",
  image: ogImageUrl({
    eyebrow: "Sell on Goods.ng",
    title: "Reach buyers across Nigeria",
    subtitle: "Post free ads, negotiate in-app and get paid safely.",
    badge: "Start selling",
  }),
  keywords: ["sell online Nigeria", "post free ads Nigeria", "sell phones Nigeria", "sell cars Nigeria", "Goods.ng seller"],
});

const BENEFITS = [
  { icon: Camera, title: "Post free ads in minutes", body: "Add photos, set your price and choose delivery options. Listing is always free." },
  { icon: Handshake, title: "Negotiate in-app", body: "Receive offers, counter, and accept. The agreed price goes straight into checkout." },
  { icon: ShieldCheck, title: "Get paid safely", body: "Protected Checkout means no fake alerts — orders are only marked paid after we verify with the payment provider." },
  { icon: Wallet, title: "Sell to more buyers", body: "Offer Goods Flex and receive the down-payment share after delivery, then the balance in monthly instalments." },
  { icon: BadgeCheck, title: "Build trust", body: "Verify your identity or business to earn the Verified badge and rank higher with buyers." },
  { icon: BarChart3, title: "Track performance", body: "See views, enquiries, contact clicks and sales from your seller dashboard." },
];

export default function Page() {
  return (
    <>
      <section className="bg-gradient-to-br from-brand-800 to-brand-950 text-white">
        <div className="container-page py-12 sm:py-16">
          <h1 className="max-w-2xl text-3xl font-extrabold tracking-tight sm:text-4xl">Sell faster to buyers across Nigeria</h1>
          <p className="mt-3 max-w-xl text-white/85">Free listings, real negotiation, and protected payments that land in your account after delivery. Withdraw to your verified bank account from your wallet.</p>
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
          <h2 className="text-xl font-bold">Goods Flex for sellers</h2>
          <p className="mt-2 text-sm text-muted">Goods Flex is opt-in per listing. You receive the buyer&apos;s 40% down-payment share after delivery, then the remaining 60% in monthly instalments over 3 or 6 months as the buyer pays. You earn <strong>70% of the 3% monthly financing charge</strong>; Goods.ng keeps 30% for checks, collections and support. If the buyer misses payments, unpaid instalments are not released to you. <Link href="/seller/flex-terms" className="font-semibold text-brand-700 underline">Read the seller terms</Link>.</p>
          <p className="mt-2 text-sm text-muted">Your email and phone must be verified. Standard commission and protection fees still apply.</p>
        </section>
        <section className="card mt-6 p-6">
          <h2 className="text-xl font-bold">Fees and payouts</h2>
          <ul className="mt-3 space-y-1.5 text-sm">
            <li>• Listing: <strong>free</strong></li>
            <li>• Commission on completed Protected Checkout sales: <strong>5% of item price</strong></li>
            <li>• Goods Flex financing charge: <strong>3% per month on the financed balance</strong> — you receive 70%</li>
            <li>• Direct (off-platform) deals: <strong>no commission</strong> — but no escrow protection</li>
            <li>• Payouts: released earnings clear for 24 hours, then withdrawals are reviewed and sent to your verified bank account; allow at least 24 hours for the transfer.</li>
          </ul>
        </section>
      </div>
    </>
  );
}
