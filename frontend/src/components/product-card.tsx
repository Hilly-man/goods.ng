import Link from "next/link";
import clsx from "clsx";
import { MapPin, Images } from "lucide-react";
import type { ProductCard as P } from "@/lib/types";
import { CONDITION_LABEL, naira, timeAgo } from "@/lib/format";
import { CategoryIcon, ROOT_CATEGORY_ICON, tintFor } from "./icons";
import { PremiumBadge, VerifiedBadge } from "./badges";
import { FavouriteButton } from "./favourite-button";

export function ProductThumb({
  src,
  alt,
  categorySlug,
  className,
  eager,
}: {
  src: string | null;
  alt: string;
  categorySlug: string;
  className?: string;
  eager?: boolean;
}) {
  if (src) {
    return (
      // Backend already serves size-optimised WebP thumbnails; lazy-load for slow networks.
      // eslint-disable-next-line @next/next/no-img-element
      <img
        src={src}
        alt={alt}
        loading={eager ? "eager" : "lazy"}
        decoding="async"
        className={clsx("size-full object-cover", className)}
      />
    );
  }
  return (
    <div className={clsx("grid size-full place-items-center", tintFor(categorySlug), className)} aria-label={alt} role="img">
      <CategoryIcon name={ROOT_CATEGORY_ICON[categorySlug]} className="size-10 opacity-70" />
    </div>
  );
}

export function ProductCard({ p, eager, compact }: { p: P; eager?: boolean; compact?: boolean }) {
  return (
    <article className="group card relative flex flex-col overflow-hidden transition hover:shadow-[var(--shadow-pop)]">
      <Link href={`/item/${p.slug}`} className="relative block aspect-[4/3] overflow-hidden bg-canvas">
        <ProductThumb src={p.thumb_url} alt={p.title} categorySlug={p.category.slug} eager={eager}
                      className="transition duration-300 group-hover:scale-[1.03]" />
        <div className="absolute left-2 top-2 flex flex-wrap gap-1">
          {p.is_featured && <span className="rounded bg-accent-500 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-ink">Featured</span>}
          {p.bnpl_enabled && <span className="rounded bg-violet-600 px-1.5 py-0.5 text-[10px] font-bold text-white">Flex</span>}
        </div>
        {p.image_count > 1 && (
          <span className="absolute bottom-2 left-2 inline-flex items-center gap-1 rounded bg-black/55 px-1.5 py-0.5 text-[11px] text-white">
            <Images className="size-3" aria-hidden />
            {p.image_count}
          </span>
        )}
      </Link>
      <FavouriteButton productId={p.id} initial={p.is_favourite} className={clsx("absolute right-2 top-2", compact && "max-sm:right-1 max-sm:top-1 max-sm:size-7")} />
      <div className={clsx("flex flex-1 flex-col", compact ? "p-2 sm:p-3" : "p-2.5 sm:p-3")}>
        <div className={clsx("font-bold text-brand-800 sm:text-base", compact ? "text-[13px]" : "text-[15px]")}>{naira(p.price)}</div>
        <Link href={`/item/${p.slug}`} className={clsx("mt-0.5 line-clamp-2 leading-snug text-ink hover:text-brand-700 sm:text-sm", compact ? "text-xs" : "text-[13px]")}>
          {p.title}
        </Link>
        <div className={clsx("mt-1.5 flex-wrap items-center gap-1", compact ? "hidden sm:flex" : "flex")}>
          <span className="rounded bg-canvas px-1.5 py-0.5 text-[11px] text-muted">{CONDITION_LABEL[p.condition]}</span>
          {p.negotiable && <span className="rounded bg-canvas px-1.5 py-0.5 text-[11px] text-muted">Negotiable</span>}
        </div>
        <div className="mt-auto flex items-center justify-between gap-1 pt-2 text-[11px] text-muted">
          <span className="inline-flex min-w-0 items-center gap-0.5 truncate">
            <MapPin className="size-3 shrink-0" aria-hidden />
            <span className="truncate">
              {p.city}, {p.state}
            </span>
          </span>
          <time className={clsx("shrink-0", compact && "hidden sm:inline")} dateTime={p.created_at} suppressHydrationWarning>{timeAgo(p.created_at)}</time>
        </div>
        {(p.seller.is_premium || p.seller.verification_level.endsWith("_verified")) && (
          <div className={clsx("mt-1.5 gap-1", compact ? "hidden sm:flex" : "flex")}>
            {p.seller.is_premium && <PremiumBadge compact />}
            <VerifiedBadge level={p.seller.verification_level} compact />
          </div>
        )}
      </div>
    </article>
  );
}

export function ProductGrid({ items, eagerCount = 0 }: { items: P[]; eagerCount?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5">
      {items.map((p, i) => (
        <ProductCard key={p.id} p={p} eager={i < eagerCount} />
      ))}
    </div>
  );
}

export function ProductGridSkeleton({ count = 10 }: { count?: number }) {
  return (
    <div className="grid grid-cols-2 gap-2.5 sm:grid-cols-3 sm:gap-3 lg:grid-cols-4 xl:grid-cols-5">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="card overflow-hidden">
          <div className="skeleton aspect-[4/3]" />
          <div className="space-y-2 p-3">
            <div className="skeleton h-4 w-1/2 rounded" />
            <div className="skeleton h-3 w-full rounded" />
            <div className="skeleton h-3 w-2/3 rounded" />
          </div>
        </div>
      ))}
    </div>
  );
}
