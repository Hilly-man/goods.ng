import type { Metadata } from "next";
import { TrackEvent } from "@/components/consent";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { ArrowRight, BadgeCheck, CalendarDays, ChevronRight, Eye, MapPin, Smile, Star, Store } from "lucide-react";
import { NotFoundError, serverGet, SITE_URL } from "@/lib/server-api";
import type { ProductCard, ProductDetail } from "@/lib/types";
import { CONDITION_LABEL, date, isVerified, naira, timeAgo, VERIFICATION_LABEL } from "@/lib/format";
import { Gallery } from "@/components/gallery";
import { ProductActions } from "@/components/product-actions";
import { ProductSpecs } from "@/components/product-specs";
import { ShareButtons } from "@/components/share-buttons";
import { FavouriteButton } from "@/components/favourite-button";
import { TrackSignal } from "@/components/recommended";
import { ProductGrid } from "@/components/product-card";
import { PremiumBadge, VerifiedBadge } from "@/components/badges";
import { SectionHeader } from "@/components/sections";
import { tintFor } from "@/components/icons";

async function getProduct(slug: string) {
  try {
    return await serverGet<ProductDetail>(`/products/${slug}`);
  } catch (e) {
    if (e instanceof NotFoundError) notFound();
    throw e;
  }
}

type Params = { params: Promise<{ slug: string }> };

export async function generateMetadata({ params }: Params): Promise<Metadata> {
  const { slug } = await params;
  const p = await getProduct(slug);
  const description = `${naira(p.price)} · ${CONDITION_LABEL[p.condition]} · ${p.city}, ${p.state}. ${p.description.slice(0, 140)}`;
  return {
    title: `${p.title} — ${naira(p.price)}`,
    description,
    alternates: { canonical: `/item/${p.slug}` },
    openGraph: { title: p.title, description, images: p.images[0] ? [{ url: p.images[0].url }] : undefined, type: "website" },
  };
}

function JsonLd({ p }: { p: ProductDetail }) {
  const data = {
    "@context": "https://schema.org",
    "@type": "Product",
    name: p.title,
    description: p.description.slice(0, 500),
    image: p.images.map((i) => (i.url.startsWith("http") ? i.url : `${SITE_URL}${i.url}`)),
    brand: p.brand ? { "@type": "Brand", name: p.brand } : undefined,
    model: p.model ?? undefined,
    category: p.category.name,
    offers: {
      "@type": "Offer",
      url: `${SITE_URL}/item/${p.slug}`,
      priceCurrency: "NGN",
      price: p.price,
      itemCondition: p.condition === "brand_new" ? "https://schema.org/NewCondition" : p.condition === "refurbished" ? "https://schema.org/RefurbishedCondition" : "https://schema.org/UsedCondition",
      availability: p.status === "active" && p.quantity > 0 ? "https://schema.org/InStock" : "https://schema.org/SoldOut",
      seller: { "@type": "Organization", name: p.seller.store_name },
    },
    aggregateRating: p.seller.rating_count > 0 ? { "@type": "AggregateRating", ratingValue: p.seller.rating_avg, reviewCount: p.seller.rating_count } : undefined,
  };
  // JSON.stringify output is escaped for "<" to prevent script injection via user content.
  return <script type="application/ld+json" dangerouslySetInnerHTML={{ __html: JSON.stringify(data).replace(/</g, "\\u003c") }} />;
}

async function Content({ params }: Params) {
  const { slug } = await params;
  const p = await getProduct(slug);
  const s = p.seller;
  return (
    <>
      <JsonLd p={p} />
      <TrackSignal kind="view" product_slug={p.slug} />
      <TrackEvent name="view_item" items={[{ id: p.id, price: p.price, name: p.title }]} value={Number(p.price)} />
      <nav aria-label="Breadcrumb" className="mb-2 flex flex-wrap items-center gap-1 text-xs text-muted">
        <Link href="/" className="hover:text-brand-700">Home</Link>
        {p.category_path.map((c) => (
          <span key={c.id} className="inline-flex items-center gap-1">
            <ChevronRight className="size-3" />
            <Link href={`/c/${c.slug}`} className="hover:text-brand-700">{c.name}</Link>
          </span>
        ))}
        {p.subcategory && (
          <span className="inline-flex items-center gap-1">
            <ChevronRight className="size-3" />
            <Link href={`/c/${p.subcategory.slug}`} className="hover:text-brand-700">{p.subcategory.name}</Link>
          </span>
        )}
      </nav>
      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_360px] xl:grid-cols-[minmax(0,1fr)_380px]">
        <div className="min-w-0 space-y-4">
          <div className="relative">
            <Gallery images={p.images} title={p.title} categorySlug={p.category.slug} />
            <div className="absolute left-3 top-3 flex flex-wrap gap-1.5">
              {s.is_premium && <span className="rounded-md bg-accent-500 px-2 py-1 text-[11px] font-bold text-ink shadow-sm">Premium</span>}
              {isVerified(s.verification_level) && (
                <span className="inline-flex items-center gap-1 rounded-md bg-white/95 px-2 py-1 text-[11px] font-semibold text-brand-800 shadow-sm">
                  <BadgeCheck className="size-3.5" /> Verified
                </span>
              )}
            </div>
            <div className="absolute right-3 top-3">
              <FavouriteButton productId={p.id} initial={p.is_favourite} />
            </div>
          </div>

          <article className="overflow-hidden rounded-2xl border border-line bg-white">
            <header className="p-4 sm:p-5">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <h1 className="text-xl font-extrabold leading-tight tracking-tight sm:text-3xl">{p.title}</h1>
                  <div className="mt-2 flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-muted">
                    {p.is_featured && <span className="rounded bg-brand-50 px-1.5 py-0.5 font-semibold text-brand-700">Promoted</span>}
                    <span className="inline-flex items-center gap-1"><MapPin className="size-3.5" />{p.city}, {p.state}</span>
                    <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />Posted <time suppressHydrationWarning>{timeAgo(p.published_at ?? p.created_at)}</time></span>
                    <span className="inline-flex items-center gap-1 sm:hidden"><Eye className="size-3.5" />{p.views_count.toLocaleString()} views</span>
                  </div>
                </div>
                <span className="hidden shrink-0 items-center gap-1 text-xs text-muted sm:flex"><Eye className="size-3.5" />{p.views_count.toLocaleString()} views</span>
              </div>
            </header>

            <section className="border-t border-line px-4 py-4 sm:px-5">
              <ProductSpecs items={[
                { label: "Condition", value: CONDITION_LABEL[p.condition] },
                ...(p.brand ? [{ label: "Brand", value: p.brand }] : []),
                ...(p.model ? [{ label: "Model", value: p.model }] : []),
                { label: "Category", value: p.category.name },
                ...(p.subcategory ? [{ label: "Subcategory", value: p.subcategory.name }] : []),
                { label: "Availability", value: p.quantity > 0 ? `${p.quantity} in stock` : "Out of stock" },
                { label: "Delivery", value: p.delivery_options.length ? p.delivery_options.map((o) => `${o.label}${Number(o.fee) ? ` · ${naira(o.fee)}` : " · Free"}`).join("\n") : "Pickup only" },
                { label: "Protected Checkout", value: p.protected_checkout_enabled ? "Yes — escrow protected" : "Not available" },
                { label: "Goods Flex", value: p.bnpl_enabled ? "Available" : "Not available" },
                { label: "Listed", value: date(p.published_at ?? p.created_at) },
              ]} />
            </section>

            <section className="border-t border-line px-4 py-4 sm:px-5">
              <h2 className="flex flex-wrap items-center gap-2 font-semibold">
                <Store className="size-5 text-brand-700" /> Store location
                <VerifiedBadge level={s.verification_level} />
              </h2>
              <p className="mt-2 flex items-center gap-1.5 text-sm font-medium"><MapPin className="size-4 text-muted" />{s.city}, {s.state}</p>
              <p className="mt-1 text-sm text-muted">Member since {date(s.member_since)} · {s.completed_sales} completed sales</p>
              <Link href={`/store/${s.slug}`} className="mt-2 inline-flex items-center gap-1 text-sm font-semibold text-brand-700 hover:underline">Visit store <ArrowRight className="size-4" /></Link>
            </section>

            <section className="border-t border-line px-4 py-4 sm:px-5">
              <h2 className="font-semibold">Description</h2>
              <p className="mt-2 whitespace-pre-line text-[15px] leading-relaxed text-ink/85">{p.description}</p>
              <ShareButtons url={`${SITE_URL}/item/${p.slug}`} title={p.title} />
            </section>

            <div className="border-t border-line px-4 py-4 sm:px-5">
              <ProductActions p={p} variant="inline" recordView={false} />
            </div>
          </article>
        </div>

        <aside className="space-y-3 lg:sticky lg:top-20 lg:self-start">
          <div id="actions" className="scroll-mt-20 rounded-2xl border border-line bg-white p-4 sm:p-5">
            <div className="flex items-baseline justify-between gap-3">
              <div className="text-2xl font-extrabold text-brand-800 sm:text-3xl">{naira(p.price)}</div>
              <span className="rounded bg-canvas px-2 py-0.5 text-[11px] font-semibold text-muted">{p.negotiable ? "Negotiable" : "Fixed price"}</span>
            </div>
            <div className="mt-4"><ProductActions p={p} /></div>
          </div>

          <Link href={`/store/${s.slug}`} className="block rounded-2xl border border-line bg-white p-4 transition hover:shadow-[var(--shadow-pop)]">
            <div className="flex items-center gap-3">
              <span className={`grid size-12 shrink-0 place-items-center overflow-hidden rounded-full text-lg font-bold ${tintFor(s.slug)}`}>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                {s.logo_url ? <img src={s.logo_url} alt="" className="size-full object-cover" /> : s.store_name[0]}
              </span>
              <div className="min-w-0">
                <p className="truncate font-semibold">{s.store_name}</p>
                <p className="flex items-center gap-1 text-xs text-muted">
                  <Star className="size-3.5 fill-accent-500 text-accent-500" />
                  {Number(s.rating_avg).toFixed(1)} ({s.rating_count} reviews) · {s.completed_sales} sales
                </p>
              </div>
            </div>
            <div className="mt-3 flex flex-wrap gap-1.5">
              {s.is_premium && <PremiumBadge />}
              <VerifiedBadge level={s.verification_level} />
              {!isVerified(s.verification_level) && <span className="rounded-full bg-canvas px-2 py-0.5 text-[11px] text-muted">{VERIFICATION_LABEL[s.verification_level]}</span>}
            </div>
            <p className="mt-2 text-xs text-muted">Member since {date(s.member_since)} · {s.city}, {s.state}</p>
            <span className="mt-2 inline-block text-sm font-semibold text-brand-700">Visit store →</span>
          </Link>

          <Link href={`/store/${s.slug}#reviews`} className="flex items-center gap-2 rounded-2xl border border-line bg-white p-4 text-sm transition hover:border-brand-300">
            <Smile className="size-5 text-accent-500" />
            <span className="font-medium">{s.rating_count > 0 ? `${Number(s.rating_avg).toFixed(1)} rating · ${s.rating_count} reviews` : "No reviews yet"}</span>
            <span className="ml-auto inline-flex items-center gap-1 font-semibold text-brand-700">View <ChevronRight className="size-4" /></span>
          </Link>

          <div className="rounded-2xl border border-line bg-white p-4 text-sm">
            <h3 className="font-semibold">Safety tips</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
              <li>Pay with Protected Checkout — never send money upfront outside Goods.ng.</li>
              <li>Inspect the item before confirming delivery.</li>
              <li>Meet in a safe, public place for pickups.</li>
              {p.delivery_options.length > 0 && <li>Confirm the delivery fee and timeline with the seller.</li>}
            </ul>
          </div>

          <Link href="/sell" className="block rounded-2xl border border-brand-200 bg-white p-3 text-center text-sm font-semibold text-brand-700 transition hover:border-brand-500">
            Post an ad like this
          </Link>
        </aside>
      </div>
      <Suspense>
        <TrustedSellers slug={p.slug} sold={p.status !== "active" || p.quantity <= 0} />
      </Suspense>
      <Suspense>
        <Similar slug={p.slug} />
      </Suspense>
      {/* Mobile: keep price and the primary action within thumb reach. */}
      <div className="fixed inset-x-0 bottom-0 z-40 flex items-center gap-2 border-t border-line bg-white/95 px-3 py-2.5 pb-[max(0.625rem,env(safe-area-inset-bottom))] backdrop-blur lg:hidden">
        <div className="min-w-0 flex-1">
          <p className="truncate text-lg font-extrabold leading-tight text-brand-800">{naira(p.price)}</p>
          <p className="text-[11px] text-muted">{p.negotiable ? "Negotiable" : "Fixed price"}</p>
        </div>
        <a href="#actions" className="inline-flex h-11 items-center rounded-lg border border-line px-3 text-sm font-semibold">Chat / Offer</a>
        {p.protected_checkout_enabled && p.status === "active" && p.quantity > 0 && (
          <Link href={`/checkout/${p.slug}`} className="inline-flex h-11 items-center rounded-lg bg-brand-700 px-4 text-sm font-bold text-white">Buy safely</Link>
        )}
      </div>
    </>
  );
}

/** Promoted block (Premium sellers' quality-checked listings from other sellers) — most useful when this item is sold. */
async function TrustedSellers({ slug, sold }: { slug: string; sold: boolean }) {
  const items = await serverGet<ProductCard[]>(`/products/${slug}/sponsored`).catch(() => [] as ProductCard[]);
  if (!items.length) return null;
  return (
    <section className="mt-8" aria-labelledby="trusted-sellers">
      <div className="mb-3 flex items-end justify-between gap-3">
        <div>
          <h2 id="trusted-sellers" className="text-lg font-bold tracking-tight sm:text-xl">{sold ? "This item is sold — you may like these" : "You may also like"}</h2>
          <p className="text-sm text-muted">Top picks from verified sellers</p>
        </div>
      </div>
      <ProductGrid items={items} placement="item" />
    </section>
  );
}

async function Similar({ slug }: { slug: string }) {
  const items = await serverGet<ProductCard[]>(`/products/${slug}/similar`);
  if (!items.length) return null;
  return (
    <section className="mt-8">
      <SectionHeader title="Similar listings" />
      <ProductGrid items={items} />
    </section>
  );
}

function DetailSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
      <div className="space-y-4"><div className="card skeleton aspect-[4/3]" /><div className="card skeleton h-60" /></div>
      <div className="card skeleton h-96" />
    </div>
  );
}

export default function ItemPage(props: Params) {
  return (
    <div className="container-page py-4 pb-24 lg:pb-4">
      <Suspense fallback={<DetailSkeleton />}>
        <Content {...props} />
      </Suspense>
    </div>
  );
}
