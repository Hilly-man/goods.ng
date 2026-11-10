import type { Metadata } from "next";
import Image from "next/image";
import Link from "next/link";
import { Suspense } from "react";
import {
  ArrowRight,
  BadgeCheck,
  CalendarClock,
  Camera,
  CheckCircle2,
  Crown,
  Flag,
  LockKeyhole,
  Handshake,
  MessageCircle,
  Phone,
  Scale,
  Search,
  ShieldAlert,
  ShieldCheck,
  Star,
  Store,
  TrendingUp,
  XCircle,
} from "lucide-react";
import { serverGet } from "@/lib/server-api";
import { ButtonLink } from "@/components/ui";
import { LiveStats, type PublicStats } from "@/components/live-stats";
import {
  BuyerIllustration,
  GrowthIllustration,
  MarketplaceIllustration,
  SafetyIllustration,
  SellerIllustration,
} from "@/components/illustrations";
import { ogImageUrl, pageMetadata } from "@/lib/seo";

export const metadata: Metadata = pageMetadata({
  title: "About Goods.ng — the safer way to buy and sell in Nigeria",
  description:
    "Goods.ng is a Nigerian marketplace where you can find great deals, negotiate in-app, pay with escrow-protected checkout or in instalments with Goods Flex, and trade with verified sellers.",
  path: "/about",
  image: ogImageUrl({
    eyebrow: "About Goods.ng",
    title: "The safer way to buy and sell in Nigeria",
    subtitle: "Escrow-protected checkout, verified sellers and Goods Flex.",
    badge: "Our story",
  }),
  keywords: ["about Goods.ng", "Nigerian marketplace", "safe online marketplace", "verified sellers Nigeria"],
});

const OUTLINE_ON_DARK =
  "inline-flex h-12 items-center justify-center gap-2 rounded-lg border border-white/40 px-5 text-base font-semibold text-white transition hover:border-white hover:bg-white/10";

export default function AboutPage() {
  return (
    <>
      <Hero />
      <div className="container-page max-w-5xl space-y-14 py-10 sm:space-y-20 sm:py-14">
        <Suspense fallback={<StatsSkeleton />}>
          <Stats />
        </Suspense>
        <WhatIs />
        <HowItWorks />
        <WhyUs />
        <TwoWays />
        <Safety />
        <SellLikeAPro />
        <Closing />
      </div>
    </>
  );
}

/* ---------- building blocks ---------- */

function Title({ children, sub }: { children: React.ReactNode; sub?: string }) {
  return (
    <div className="text-center">
      <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">{children}</h2>
      {sub && <p className="mx-auto mt-2 max-w-xl text-muted">{sub}</p>}
    </div>
  );
}

/* ---------- sections ---------- */

function Hero() {
  return (
    <section className="relative isolate overflow-hidden bg-brand-900 text-white">
      <Image
        src="/about/lagos-ikoyi-skyline.webp"
        alt="Aerial view of Ikoyi, Lagos — green neighbourhoods, the lagoon and the city skyline"
        fill
        priority
        sizes="100vw"
        className="-z-10 object-cover object-[center_65%] grayscale-[30%]"
      />
      <div className="absolute inset-0 -z-10 bg-gradient-to-br from-brand-800/80 via-brand-700/70 to-brand-900/85" />
      <div className="container-page max-w-3xl py-16 text-center sm:py-24">
        <p className="inline-flex items-center gap-2 rounded-full bg-white/10 px-3 py-1 text-sm font-semibold ring-1 ring-white/20 backdrop-blur">
          <ShieldCheck className="size-4 text-accent-400" /> Buy. Sell. Trade with Confidence.
        </p>
        <h1 className="mt-4 text-3xl font-extrabold leading-tight tracking-tight drop-shadow sm:text-5xl">
          The safer way to buy and sell <span className="whitespace-nowrap text-accent-400">in Nigeria</span>
        </h1>
        <p className="mx-auto mt-4 max-w-xl text-white/90 sm:text-lg">
          Find great deals, agree a price with the seller, and pay safely — in full or in instalments.
        </p>
        <div className="mt-7 flex flex-wrap justify-center gap-3">
          <ButtonLink href="/search" variant="accent" size="lg">Start shopping <ArrowRight className="size-5" /></ButtonLink>
          <Link href="/seller/onboarding" className={OUTLINE_ON_DARK}>Start selling</Link>
        </div>
      </div>
    </section>
  );
}

async function Stats() {
  // Real counts from the database, seeded on the server then refreshed in the browser by LiveStats.
  const initial = await serverGet<PublicStats>("/stats/public");
  return <LiveStats initial={initial} />;
}

function StatsSkeleton() {
  return <div className="grid grid-cols-2 gap-3 pt-8 lg:grid-cols-4">{[0, 1, 2, 3].map((i) => <div key={i} className="card skeleton h-32" />)}</div>;
}

function WhatIs() {
  return (
    <section className="grid items-center gap-8 md:grid-cols-2">
      <MarketplaceIllustration className="mx-auto w-full max-w-md" />
      <div className="text-center md:text-left">
        <h2 className="text-2xl font-extrabold tracking-tight sm:text-3xl">What is Goods.ng?</h2>
        <p className="mt-4 text-lg leading-relaxed text-ink/85">
          Goods.ng is an online marketplace for everything from phones and cars to fashion and property.
          We add what classifieds sites are missing: <b>payments held safely until you receive your item</b>,
          in-app negotiation, pay-later options and verified sellers.
        </p>
      </div>
    </section>
  );
}

function StepList({ steps }: { steps: { icon: React.ElementType; text: React.ReactNode }[] }) {
  return (
    <ol className="space-y-4">
      {steps.map((s, i) => (
        <li key={i} className="flex items-start gap-3">
          <span className="grid size-9 shrink-0 place-items-center rounded-full bg-brand-700 text-sm font-bold text-white">{i + 1}</span>
          <p className="pt-1.5 text-[15px] leading-snug"><s.icon className="mr-1.5 inline size-4 -translate-y-px text-brand-700" />{s.text}</p>
        </li>
      ))}
    </ol>
  );
}

function HowItWorks() {
  return (
    <section>
      <Title sub="Three simple steps either way.">How it works</Title>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="card flex flex-col overflow-hidden">
          <div className="bg-brand-50/60 px-6 pt-5"><BuyerIllustration className="mx-auto h-44 w-auto sm:h-48" /></div>
          <div className="flex flex-1 flex-col p-6">
          <h3 className="text-lg font-bold">Buying</h3>
          <div className="mt-4 flex-1">
            <StepList steps={[
              { icon: Search, text: <><b>Find it.</b> Search or browse, then filter by location, price and condition.</> },
              { icon: Handshake, text: <><b>Agree a price.</b> Chat with the seller and make an offer.</> },
              { icon: ShieldCheck, text: <><b>Pay safely.</b> Your money is released to the seller only after you confirm delivery.</> },
            ]} />
          </div>
          <ButtonLink href="/search" className="mt-6" block>Start shopping</ButtonLink>
          </div>
        </div>
        <div className="card flex flex-col overflow-hidden">
          <div className="bg-amber-50/60 px-6 pt-5"><SellerIllustration className="mx-auto h-44 w-auto sm:h-48" /></div>
          <div className="flex flex-1 flex-col p-6">
          <h3 className="text-lg font-bold">Selling</h3>
          <div className="mt-4 flex-1">
            <StepList steps={[
              { icon: Store, text: <><b>Set up your store.</b> Free — it takes about two minutes.</> },
              { icon: Camera, text: <><b>Post your item.</b> Add photos, a price and delivery options.</> },
              { icon: MessageCircle, text: <><b>Sell and get paid.</b> Reply to buyers, ship the order, get paid on delivery.</> },
            ]} />
          </div>
          <p className="mt-5 flex items-center gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            <Crown className="size-4 shrink-0" />Want more buyers? <Link href="/premium" className="font-semibold underline">Go Premium</Link>
          </p>
          <ButtonLink href="/seller/onboarding" variant="outline" className="mt-3" block>Start selling</ButtonLink>
          </div>
        </div>
      </div>
    </section>
  );
}

function WhyUs() {
  const items = [
    { icon: ShieldCheck, tone: "bg-brand-50 text-brand-700", title: "Protected payments", body: "We hold your money until you get your item." },
    { icon: Handshake, tone: "bg-amber-50 text-amber-700", title: "Negotiate in-app", body: "Make offers; the agreed price goes to checkout." },
    { icon: CalendarClock, tone: "bg-accent-500/25 text-brand-800", title: "Pay small-small", body: "Pay 40% today, then spread the remaining 60% over 3 or 6 months with Goods Flex." },
    { icon: BadgeCheck, tone: "bg-sky-50 text-sky-700", title: "Verified sellers", body: "Look for the badge and real buyer reviews." },
  ];
  return (
    <section>
      <Title>Why people choose Goods.ng</Title>
      <div className="mt-8 grid grid-cols-2 gap-3 lg:grid-cols-4">
        {items.map((d) => (
          <div key={d.title} className="card p-5 text-center">
            <span className={`mx-auto grid size-12 place-items-center rounded-2xl ${d.tone}`}><d.icon className="size-6" /></span>
            <h3 className="mt-3 font-bold">{d.title}</h3>
            <p className="mt-1 text-sm text-muted">{d.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

function TwoWays() {
  const yes = (t: string) => <li className="flex gap-2"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-brand-600" />{t}</li>;
  const no = (t: string) => <li className="flex gap-2"><XCircle className="mt-0.5 size-4 shrink-0 text-red-500" />{t}</li>;
  return (
    <section>
      <Title sub="Both are allowed — but only one protects your money.">Two ways to buy</Title>
      <div className="mt-8 grid gap-4 md:grid-cols-2">
        <div className="card p-6 ring-2 ring-brand-600">
          <p className="flex flex-wrap items-center gap-2 font-bold"><ShieldCheck className="size-5 text-brand-700" />Pay through Goods.ng <span className="ml-auto rounded-full bg-brand-700 px-2 py-0.5 text-xs text-white">Recommended</span></p>
          <ul className="mt-4 space-y-2 text-sm">
            {yes("Money held until you confirm delivery")}
            {yes("Help from us if something goes wrong")}
            {yes("Option to pay in instalments")}
          </ul>
        </div>
        <div className="card p-6">
          <p className="flex items-center gap-2 font-bold"><Phone className="size-5 text-muted" />Deal directly (WhatsApp / call)</p>
          <ul className="mt-4 space-y-2 text-sm">
            {yes("Quick chats and inspections")}
            {no("No payment protection")}
            {no("We can't help with disputes")}
          </ul>
        </div>
      </div>
    </section>
  );
}

function Feature({ icon: Icon, title, children }: { icon: React.ElementType; title: string; children: React.ReactNode }) {
  return (
    <li className="flex gap-3">
      <span className="grid size-9 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700"><Icon className="size-5" /></span>
      <div>
        <h3 className="font-bold">{title}</h3>
        <p className="mt-0.5 text-[15px] leading-snug text-ink/80">{children}</p>
      </div>
    </li>
  );
}

function Safety() {
  const tips = [
    "Pay only through Goods.ng — never transfer money to a seller directly.",
    "Ignore payment screenshots or \"alerts\" — check the order on Goods.ng.",
    "Inspect items in a busy, public place before you accept them.",
    "Never share your OTP, PIN or password — our staff will never ask.",
  ];
  return (
    <section className="grid items-start gap-8 md:grid-cols-2 md:gap-12">
      <SafetyIllustration className="mx-auto w-full max-w-md md:sticky md:top-24" />
      <div>
        <h2 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
          <ShieldAlert className="size-7 text-brand-700" />Safety
        </h2>
        <p className="mt-2 text-ink/80">Built into every step, so you don&apos;t have to rely on trust alone.</p>
        <ul className="mt-6 space-y-5">
          <Feature icon={ShieldCheck} title="Protected Checkout">
            Your payment is held by our licensed payment partner, not the seller. It&apos;s released when you confirm
            delivery — or automatically 3 days after delivery if you don&apos;t raise a problem.
          </Feature>
          <Feature icon={Scale} title="Disputes, handled by people">
            Item not delivered or not as described? Open a dispute from your order and the money stays held while our team reviews it.
          </Feature>
          <Feature icon={BadgeCheck} title="Verified sellers & honest reviews">
            Sellers verify their phone, ID or business. Reviews come only from completed orders or real conversations — never bought.
          </Feature>
          <Feature icon={Flag} title="Report anything suspicious">
            Every listing and message has a Report button. Our moderators check reports and remove scammers fast.
          </Feature>
          <Feature icon={LockKeyhole} title="Keep your account locked">
            Turn on two-step login in <Link href="/account" className="font-semibold text-brand-700 hover:underline">your account</Link>, and
            keep chats in Goods.ng — we warn you before you switch to WhatsApp or a call, where we can&apos;t protect you.
          </Feature>
        </ul>
        <div className="mt-7 rounded-2xl bg-amber-50 p-5">
          <p className="font-bold text-amber-900">Personal safety tips</p>
          <ul className="mt-3 space-y-2">
            {tips.map((t) => (
              <li key={t} className="flex gap-2 text-[15px] text-amber-950"><CheckCircle2 className="mt-0.5 size-4 shrink-0 text-amber-600" />{t}</li>
            ))}
          </ul>
        </div>
        <p className="mt-4 text-sm"><Link href="/buyer-protection" className="font-semibold text-brand-700 hover:underline">How buyer & seller protection works →</Link></p>
      </div>
    </section>
  );
}

function SellLikeAPro() {
  return (
    <section className="grid items-start gap-8 md:grid-cols-2 md:gap-12">
      <GrowthIllustration className="mx-auto w-full max-w-md md:order-2 md:sticky md:top-24" />
      <div className="md:order-1">
        <h2 className="flex items-center gap-2 text-2xl font-extrabold tracking-tight sm:text-3xl">
          <TrendingUp className="size-7 text-brand-700" />Sell like a pro!
        </h2>
        <ol className="mt-6 space-y-5">
          <Feature icon={Camera} title="1. Pay attention to the details">
            Take clear photos in good light, write an honest description, and pick the right category, condition and location.
          </Feature>
          <Feature icon={MessageCircle} title="2. Answer quickly">
            Buyers move on fast. Turn on <Link href="/account/notifications" className="font-semibold text-brand-700 hover:underline">notifications</Link> and
            reply to messages and offers within the hour.
          </Feature>
          <Feature icon={ShieldCheck} title="3. Offer Protected Checkout">
            Buyers trust it more, and you&apos;re paid on delivery — no fake transfer alerts.
          </Feature>
          <Feature icon={BadgeCheck} title="4. Get verified">
            <Link href="/seller/verification" className="font-semibold text-brand-700 hover:underline">Verify your ID or business</Link> to
            earn a badge that buyers look for.
          </Feature>
          <Feature icon={Crown} title="5. Go Premium to reach more buyers">
            A Premium Seller badge, WhatsApp and call buttons, featured listing credits and priority in search
            put your ads in front of more people.
          </Feature>
        </ol>
        <div className="mt-7 flex flex-wrap gap-3">
          <ButtonLink href="/premium" variant="accent" size="lg"><Crown className="size-5" />Go Premium</ButtonLink>
          <ButtonLink href="/seller/onboarding" variant="outline" size="lg">Start selling</ButtonLink>
        </div>
      </div>
    </section>
  );
}

function Closing() {
  return (
    <section className="rounded-3xl bg-gradient-to-br from-brand-800 to-brand-950 p-8 text-center text-white sm:p-12">
      <Star className="mx-auto size-8 text-accent-400" />
      <h2 className="mt-3 text-2xl font-extrabold sm:text-3xl">Questions?</h2>
      <p className="mx-auto mt-2 max-w-md text-white/80">Fees, delivery, disputes and Goods Flex are all covered in our FAQ.</p>
      <div className="mt-6 flex flex-wrap justify-center gap-3">
        <ButtonLink href="/faq" variant="accent" size="lg">Read the FAQ</ButtonLink>
        <Link href="/contact" className={OUTLINE_ON_DARK}>Contact us</Link>
      </div>
    </section>
  );
}
