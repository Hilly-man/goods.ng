import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { CalendarDays, ChevronRight, Eye, MapPin, Star, Truck } from "lucide-react";
import { NotFoundError, serverGet, SITE_URL } from "@/lib/server-api";
import type { ProductCard, ProductDetail } from "@/lib/types";
import { CONDITION_LABEL, date, naira, timeAgo, VERIFICATION_LABEL } from "@/lib/format";
import { Gallery } from "@/components/gallery";
import { ProductActions } from "@/components/product-actions";
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
      <nav aria-label="Breadcrumb" className="mb-3 flex flex-wrap items-center gap-1 text-xs text-muted">
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
      <div className="grid gap-5 lg:grid-cols-[1fr_380px]">
        <div className="min-w-0 space-y-4">
          <Gallery images={p.images} title={p.title} categorySlug={p.category.slug} />
          <section className="card p-4 sm:p-5">
            <h1 className="text-lg font-bold leading-snug sm:text-2xl">{p.title}</h1>
            <div className="mt-1.5 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted">
              <span className="inline-flex items-center gap-1"><MapPin className="size-3.5" />{p.city}, {p.state}</span>
              <span className="inline-flex items-center gap-1"><CalendarDays className="size-3.5" />Posted <time suppressHydrationWarning>{timeAgo(p.published_at ?? p.created_at)}</time></span>
              <span className="inline-flex items-center gap-1"><Eye className="size-3.5" />{p.views_count.toLocaleString()} views</span>
            </div>
            <dl className="mt-4 grid grid-cols-2 gap-3 border-y border-line py-4 text-sm sm:grid-cols-4">
              <div><dt className="text-xs text-muted">Condition</dt><dd className="font-semibold">{CONDITION_LABEL[p.condition]}</dd></div>
              {p.brand && <div><dt className="text-xs text-muted">Brand</dt><dd className="font-semibold">{p.brand}</dd></div>}
              {p.model && <div><dt className="text-xs text-muted">Model</dt><dd className="font-semibold">{p.model}</dd></div>}
              <div><dt className="text-xs text-muted">Availability</dt><dd className="font-semibold">{p.quantity > 0 ? `${p.quantity} in stock` : "Out of stock"}</dd></div>
            </dl>
            <h2 className="mt-4 font-semibold">Description</h2>
            <p className="mt-1.5 whitespace-pre-line text-[15px] leading-relaxed text-ink/85">{p.description}</p>
          </section>
          <section className="card p-4 sm:p-5">
            <h2 className="flex items-center gap-2 font-semibold"><Truck className="size-5 text-brand-700" /> Delivery options</h2>
            <ul className="mt-3 divide-y divide-line">
              {p.delivery_options.map((o, i) => (
                <li key={i} className="flex items-center justify-between py-2.5 text-sm">
                  <span>{o.label}<span className="block text-xs text-muted">{o.eta_days ? `About ${o.eta_days} day${o.eta_days > 1 ? "s" : ""}` : "Same day"}</span></span>
                  <span className="font-semibold">{Number(o.fee) === 0 ? "Free" : naira(o.fee)}</span>
                </li>
              ))}
            </ul>
          </section>
        </div>
        <aside className="space-y-4 lg:sticky lg:top-20 lg:self-start">
          <div id="actions" className="card scroll-mt-20 p-4 sm:p-5">
            <div className="text-2xl font-extrabold text-brand-800 sm:text-3xl">{naira(p.price)}</div>
            <div className="mt-1 flex gap-1.5 text-xs">
              {p.negotiable ? <span className="rounded bg-brand-50 px-2 py-0.5 font-semibold text-brand-800">Negotiable</span> : <span className="rounded bg-canvas px-2 py-0.5 font-semibold text-muted">Fixed price</span>}
            </div>
            <div className="mt-4"><ProductActions p={p} /></div>
          </div>
          <Link href={`/store/${s.slug}`} className="card block p-4 hover:shadow-[var(--shadow-pop)]">
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
              {!s.verification_level.endsWith("_verified") || s.verification_level === "phone_verified" ? (
                <span className="rounded-full bg-canvas px-2 py-0.5 text-[11px] text-muted">{VERIFICATION_LABEL[s.verification_level]}</span>
              ) : null}
            </div>
            <p className="mt-2 text-xs text-muted">Member since {date(s.member_since)} · {s.city}, {s.state}</p>
            <span className="mt-2 inline-block text-sm font-semibold text-brand-700">Visit store →</span>
          </Link>
          <div className="card p-4 text-sm">
            <h3 className="font-semibold">Safety tips</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-muted">
              <li>Pay with Protected Checkout — never send money upfront outside Goods.ng.</li>
              <li>Inspect the item before confirming delivery.</li>
              <li>Meet in a safe, public place for pickups.</li>
            </ul>
          </div>
        </aside>
      </div>
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
