import Link from "next/link";
import { Suspense } from "react";
import { ArrowRight, BadgeCheck, CalendarClock, Handshake, MessagesSquare, PackageCheck, ShieldCheck, Wallet } from "lucide-react";
import { serverGet } from "@/lib/server-api";
import type { Category, HomeFeed } from "@/lib/types";
import { ProductGridSkeleton } from "@/components/product-card";
import { ProductCollection } from "@/components/product-collection";
import { ViewToggle } from "@/components/view-toggle";
import { FeaturedCarousel } from "@/components/featured-carousel";
import { AutoCarousel } from "@/components/auto-carousel";
import { CategoryTiles, SectionHeader, SellerTile } from "@/components/sections";
import { CategoryMenu } from "@/components/category-menu";
import { RecommendedForYou } from "@/components/recommended";

export default function HomePage() {
  return (
    <>
      <Hero />
      <div className="container-page mt-4 grid gap-6 lg:grid-cols-[280px_1fr]">
        <aside className="relative z-20 hidden lg:block">
          <Suspense fallback={<div className="card skeleton h-[640px]" />}>
            <Categories variant="sidebar" />
          </Suspense>
        </aside>
        <div className="min-w-0 space-y-8">
          <div className="lg:hidden">
            <Suspense fallback={<div className="skeleton h-[500px] rounded-xl" />}>
              <Categories variant="tiles" />
            </Suspense>
          </div>
          <TrustStrip />
          <Suspense fallback={<FeedSkeleton />}>
            <Feed />
          </Suspense>
          <HowItWorks />
        </div>
      </div>
    </>
  );
}

async function Categories({ variant }: { variant: "sidebar" | "tiles" }) {
  const cats = await serverGet<Category[]>("/categories");
  return variant === "sidebar" ? <CategoryMenu categories={cats} /> : <CategoryTiles categories={cats} />;
}

function Hero() {
  return (
    <section className="bg-gradient-to-b from-brand-800 to-brand-700 text-white">
      <div className="container-page flex flex-col gap-4 pb-4 pt-3 sm:pb-8 sm:pt-6 md:flex-row md:items-end md:justify-between">
        <div className="max-w-2xl">
          <h1 className="text-xl font-extrabold tracking-tight sm:text-3xl lg:text-4xl">
            Buy. Sell. Trade with <span className="text-accent-400">Confidence.</span>
          </h1>
          <p className="mt-1.5 hidden text-sm text-white/85 sm:block sm:text-base">
            Thousands of listings across Nigeria. Chat and negotiate directly, pay safely with Protected Checkout, or spread
            the cost with Goods Flex.
          </p>
        </div>
        <div className="hidden flex-wrap gap-2 text-xs font-semibold sm:flex sm:text-sm">
          <Pill icon={<ShieldCheck className="size-4" />}>Escrow protection</Pill>
          <Pill icon={<CalendarClock className="size-4" />}>Pay in instalments</Pill>
          <Pill icon={<BadgeCheck className="size-4" />}>Verified sellers</Pill>
        </div>
      </div>
    </section>
  );
}

function Pill({ icon, children }: { icon: React.ReactNode; children: React.ReactNode }) {
  return <span className="inline-flex items-center gap-1.5 rounded-full bg-white/12 px-3 py-1.5 ring-1 ring-white/20">{icon}{children}</span>;
}

function TrustStrip() {
  return (
    <div className="grid gap-3 md:grid-cols-2">
      <Link href="/buyer-protection" className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-brand-700 to-brand-900 p-5 text-white">
        <ShieldCheck className="absolute -right-4 -top-4 size-32 text-white/10" aria-hidden />
        <p className="text-xs font-bold uppercase tracking-wider text-accent-400">Buyer Protection</p>
        <h2 className="mt-1 text-lg font-bold sm:text-xl">Your money is safeguarded until you confirm delivery</h2>
        <p className="mt-1 max-w-md text-sm text-white/80">Pay with Goods.ng Protected Checkout. If the item doesn&apos;t arrive or isn&apos;t as described, we step in.</p>
        <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold">Learn how it works <ArrowRight className="size-4 transition group-hover:translate-x-0.5" /></span>
      </Link>
      <Link href="/flex/about" className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-violet-600 to-indigo-800 p-5 text-white">
        <Wallet className="absolute -right-4 -top-4 size-32 text-white/10" aria-hidden />
        <p className="text-xs font-bold uppercase tracking-wider text-violet-200">Goods Flex</p>
        <h2 className="mt-1 text-lg font-bold sm:text-xl">Buy now, pay in 3 or 6 monthly instalments</h2>
        <p className="mt-1 max-w-md text-sm text-white/80">Pay a down payment today and spread the rest. Financing by our licensed lending partner, subject to approval.</p>
        <span className="mt-3 inline-flex items-center gap-1 text-sm font-semibold">Check eligibility <ArrowRight className="size-4 transition group-hover:translate-x-0.5" /></span>
      </Link>
    </div>
  );
}

async function Feed() {
  const feed = await serverGet<HomeFeed>("/products/feed/home");
  return (
    <>
      {feed.featured.length > 0 && (
        <section>
          <SectionHeader title="Featured listings" sub="Promoted by sellers" href="/search?sort=relevance" />
          <FeaturedCarousel items={feed.featured} />
        </section>
      )}
      <section>
        <SectionHeader title="Trending now" sub="Most viewed and saved this month" href="/search" action={<ViewToggle />} />
        <ProductCollection items={feed.trending.slice(0, 10)} eagerCount={feed.featured.length ? 0 : 4} />
      </section>
      <RecommendedForYou />
      <section>
        <SectionHeader title="Recently listed" sub="Fresh ads from across Nigeria" href="/search?sort=newest" />
        <ProductCollection items={feed.recent.slice(0, 15)} />
      </section>
      {feed.verified_sellers.length > 0 && (
        <section>
          <SectionHeader title="Verified sellers" sub="Identity or business verified by Goods.ng" href="/search?verified=true" />
          {/* One row that scrolls to the left on its own: ~1.4 per view on phones, 2 on tablets, 3 on desktop. */}
          <AutoCarousel label="Verified sellers"
            slideClassName="basis-[72%] sm:basis-[calc((100%-0.75rem)/2)] lg:basis-[calc((100%-1.5rem)/3)] [&>a]:w-full">
            {feed.verified_sellers.map((s) => <SellerTile key={s.id} s={s} />)}
          </AutoCarousel>
        </section>
      )}
    </>
  );
}

function FeedSkeleton() {
  return (
    <div className="space-y-3">
      <div className="skeleton h-6 w-40 rounded" />
      <ProductGridSkeleton count={10} />
    </div>
  );
}

function HowItWorks() {
  const steps = [
    { icon: MessagesSquare, title: "Find & chat", body: "Search thousands of listings, chat with sellers in-app and ask questions." },
    { icon: Handshake, title: "Negotiate", body: "Make an offer. Sellers can accept, decline or counter — the agreed price carries into checkout." },
    { icon: ShieldCheck, title: "Pay protected", body: "Pay through Protected Checkout. Funds are held by our licensed escrow partner." },
    { icon: PackageCheck, title: "Confirm & done", body: "Inspect your item and confirm. Only then is the seller paid. Problems? Open a dispute." },
  ];
  return (
    <section className="card p-5 sm:p-6">
      <SectionHeader title="How Goods.ng works" href="/how-it-works" />
      <ol className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {steps.map((s, i) => (
          <li key={s.title} className="flex gap-3">
            <span className="grid size-10 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-700">
              <s.icon className="size-5" />
            </span>
            <div>
              <p className="text-sm font-semibold">{i + 1}. {s.title}</p>
              <p className="mt-0.5 text-sm text-muted">{s.body}</p>
            </div>
          </li>
        ))}
      </ol>
      <p className="mt-4 rounded-lg bg-amber-50 p-3 text-xs text-amber-900 ring-1 ring-amber-200">
        Prefer to deal directly? Premium sellers can be reached by WhatsApp or phone. Deals completed outside Goods.ng
        Protected Checkout are not covered by escrow protection or our dispute process.
      </p>
    </section>
  );
}
