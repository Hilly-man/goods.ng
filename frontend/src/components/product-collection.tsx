"use client";

import Link from "next/link";
import { MapPin, ShieldCheck } from "lucide-react";
import type { ProductCard as P } from "@/lib/types";
import { CONDITION_LABEL, naira, timeAgo } from "@/lib/format";
import { ProductGrid, ProductThumb } from "./product-card";
import { FavouriteButton } from "./favourite-button";
import { FlexBadge, VerifiedBadge } from "./badges";
import { AdTracker, SponsoredLabel } from "./ad-tracker";
import type { AdPlacement } from "@/lib/ads";
import { useListingView } from "./view-toggle";

export function ProductRow({ p, eager, placement = "search" }: { p: P; eager?: boolean; placement?: AdPlacement }) {
  return (
    <article className="card group relative flex overflow-hidden transition hover:shadow-[var(--shadow-pop)]">
      <Link href={`/item/${p.slug}`} className="relative block w-32 shrink-0 overflow-hidden bg-canvas sm:w-56">
        <ProductThumb src={p.thumb_url} alt={p.title} categorySlug={p.category.slug} eager={eager}
          className="transition duration-300 group-hover:scale-[1.03]" />
        <span className="absolute left-2 top-2 flex flex-wrap gap-1">
          {p.sponsored && <SponsoredLabel />}
          {p.is_featured && <span className="rounded bg-accent-500 px-1.5 py-0.5 text-[10px] font-bold uppercase text-ink">Featured</span>}
        </span>
      </Link>
      {p.sponsored && <AdTracker productId={p.id} placement={placement} />}
      <div className="flex min-w-0 flex-1 flex-col gap-1 p-3 sm:p-4">
        <div className="flex items-start justify-between gap-2">
          <div className="text-lg font-bold text-brand-800 sm:text-xl">{naira(p.price)}</div>
          <FavouriteButton productId={p.id} initial={p.is_favourite} className="shrink-0 border border-line" />
        </div>
        <Link href={`/item/${p.slug}`} className="line-clamp-2 text-[15px] font-medium leading-snug hover:text-brand-700 sm:text-base">{p.title}</Link>
        <p className="flex items-center gap-1 text-xs text-muted">
          <MapPin className="size-3.5 shrink-0" />
          <span className="truncate">{p.city}, {p.state}</span>
          <span aria-hidden>·</span>
          <time className="shrink-0" dateTime={p.created_at} suppressHydrationWarning>{timeAgo(p.created_at)}</time>
        </p>
        <div className="mt-auto flex flex-wrap items-center gap-1.5 pt-1.5">
          <span className="rounded bg-canvas px-2 py-0.5 text-xs font-medium text-ink/80">{CONDITION_LABEL[p.condition]}</span>
          {p.negotiable && <span className="rounded bg-canvas px-2 py-0.5 text-xs font-medium text-ink/80">Negotiable</span>}
          {p.protected_checkout_enabled && (
            <span className="hidden items-center gap-1 rounded bg-brand-50 px-2 py-0.5 text-xs font-semibold text-brand-800 sm:inline-flex">
              <ShieldCheck className="size-3.5" />Protected
            </span>
          )}
          {p.bnpl_enabled && <FlexBadge />}
          <VerifiedBadge level={p.seller.verification_level} compact />
          <span className="ml-auto hidden truncate text-xs text-muted sm:block">{p.seller.store_name}</span>
        </div>
      </div>
    </article>
  );
}

/** Renders listings as a grid or as rows, following the user's saved layout preference. */
export function ProductCollection({ items, eagerCount = 0, placement }: { items: P[]; eagerCount?: number; placement?: AdPlacement }) {
  const [view] = useListingView();
  if (view === "list") {
    return (
      <div className="flex flex-col gap-2.5 sm:gap-3">
        {items.map((p, i) => <ProductRow key={p.id} p={p} eager={i < eagerCount} placement={placement} />)}
      </div>
    );
  }
  return <ProductGrid items={items} eagerCount={eagerCount} placement={placement} />;
}
