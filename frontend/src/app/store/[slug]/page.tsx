import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { Clock, Globe, MapPin, ShieldCheck, Star } from "lucide-react";
import { NotFoundError, serverGet } from "@/lib/server-api";
import type { Page, ProductCard, Review, Storefront } from "@/lib/types";
import { date } from "@/lib/format";
import { ProductCollection } from "@/components/product-collection";
import { ViewToggle } from "@/components/view-toggle";
import { PremiumBadge, VerifiedBadge } from "@/components/badges";
import { tintFor } from "@/components/icons";
import { SectionHeader } from "@/components/sections";
import { StoreContact } from "@/components/store-contact";

type Params = { params: Promise<{ slug: string }> };

async function getStore(slug: string) {
  try {
    return await serverGet<Storefront>(`/sellers/${slug}`);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
}

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const s = await getStore(slug);
  return {
    title: `${s.store_name} — ${s.city ?? ""} ${s.state ?? ""}`.trim(),
    description: s.description?.slice(0, 160) ?? `Shop ${s.store_name} on Goods.ng.`,
    alternates: { canonical: `/store/${s.slug}` },
  };
}

async function Content({ params }: Params) {
  const { slug } = await params;
  const [s, products, reviews] = await Promise.all([
    getStore(slug),
    serverGet<Page<ProductCard>>(`/sellers/${slug}/products`, { page_size: "40" }),
    serverGet<Page<Review> & { summary: { average: string; count: number; distribution: Record<string, number> } }>(`/sellers/${slug}/reviews`, { page_size: "6" }),
  ]);
  return (
    <>
      <section className="card overflow-hidden">
        <div className="h-28 bg-gradient-to-r from-brand-700 via-brand-600 to-brand-800 sm:h-40">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          {s.banner_url && <img src={s.banner_url} alt="" className="size-full object-cover" />}
        </div>
        <div className="flex flex-col gap-4 p-4 sm:flex-row sm:items-end sm:p-5">
          <span className={`-mt-14 grid size-20 shrink-0 place-items-center overflow-hidden rounded-2xl text-3xl font-bold ring-4 ring-white sm:-mt-16 sm:size-24 ${tintFor(s.slug)}`}>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            {s.logo_url ? <img src={s.logo_url} alt="" className="size-full object-cover" /> : s.store_name[0]}
          </span>
          <div className="min-w-0 flex-1">
            <div className="flex flex-wrap items-center gap-2">
              <h1 className="text-xl font-bold sm:text-2xl">{s.store_name}</h1>
              {s.is_premium && <PremiumBadge />}
              <VerifiedBadge level={s.verification_level} />
            </div>
            <div className="mt-1 flex flex-wrap gap-x-4 gap-y-1 text-sm text-muted">
              <span className="inline-flex items-center gap-1"><Star className="size-4 fill-accent-500 text-accent-500" />{Number(s.rating_avg).toFixed(1)} ({s.rating_count})</span>
              <span>{s.completed_sales} completed sales</span>
              <span className="inline-flex items-center gap-1"><MapPin className="size-4" />{s.city}, {s.state}</span>
              <span>Member since {date(s.member_since)}</span>
              {s.business_hours && <span className="inline-flex items-center gap-1"><Clock className="size-4" />{s.business_hours}</span>}
              {s.website && <a href={s.website} rel="nofollow noopener noreferrer" target="_blank" className="inline-flex items-center gap-1 text-brand-700 hover:underline"><Globe className="size-4" />Website</a>}
            </div>
            {s.description && <p className="mt-2 max-w-3xl text-sm text-ink/85">{s.description}</p>}
          </div>
          <StoreContact seller={s} />
        </div>
      </section>
      <section className="mt-6">
        <SectionHeader title={`Listings (${s.active_listings})`} action={<ViewToggle />} />
        {products.items.length ? <ProductCollection items={products.items} eagerCount={4} /> : <p className="card p-6 text-center text-sm text-muted">No active listings right now.</p>}
      </section>
      <section className="mt-8 grid gap-4 lg:grid-cols-[280px_1fr]">
        <div className="card p-5">
          <h2 className="font-semibold">Ratings</h2>
          <p className="mt-2 text-4xl font-extrabold">{Number(reviews.summary.average).toFixed(1)}</p>
          <p className="text-sm text-muted">{reviews.summary.count} reviews</p>
          <ul className="mt-3 space-y-1.5">
            {Object.entries(reviews.summary.distribution).map(([k, v]) => (
              <li key={k} className="flex items-center gap-2 text-xs">
                <span className="w-3">{k}</span>
                <span className="h-2 flex-1 overflow-hidden rounded-full bg-canvas">
                  <span className="block h-full bg-accent-500" style={{ width: `${reviews.summary.count ? (v / reviews.summary.count) * 100 : 0}%` }} />
                </span>
                <span className="w-6 text-right text-muted">{v}</span>
              </li>
            ))}
          </ul>
        </div>
        <div className="space-y-3">
          {reviews.items.length === 0 && <p className="card p-6 text-sm text-muted">No reviews yet.</p>}
          {reviews.items.map((r) => (
            <article key={r.id} className="card p-4">
              <div className="flex items-center justify-between">
                <span className="flex">{Array.from({ length: 5 }).map((_, i) => <Star key={i} className={`size-4 ${i < r.rating ? "fill-accent-500 text-accent-500" : "text-line"}`} />)}</span>
                <span className="text-xs text-muted">{date(r.created_at)}</span>
              </div>
              {r.title && <h3 className="mt-1.5 font-semibold">{r.title}</h3>}
              {r.comment && <p className="mt-1 text-sm text-ink/85">{r.comment}</p>}
              <p className="mt-2 flex items-center gap-2 text-xs text-muted">
                {r.reviewer}
                {r.is_verified_purchase && <span className="inline-flex items-center gap-1 font-semibold text-brand-700"><ShieldCheck className="size-3.5" />Verified purchase</span>}
              </p>
              {r.seller_reply && <p className="mt-2 rounded-lg bg-canvas p-2.5 text-sm"><span className="font-semibold">Seller reply: </span>{r.seller_reply}</p>}
            </article>
          ))}
        </div>
      </section>
    </>
  );
}

export default function StorePage(props: Params) {
  return (
    <div className="container-page py-4">
      <Suspense fallback={<div className="card skeleton h-64" />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}
