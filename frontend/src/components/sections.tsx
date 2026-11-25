import Link from "next/link";
import { byListings } from "@/lib/format";
import { ChevronRight, Star } from "lucide-react";
import type { Category, SellerCard } from "@/lib/types";
import { CategoryIcon, tintFor } from "./icons";
import { VerifiedBadge } from "./badges";
import { AutoCarousel } from "./auto-carousel";

export function SectionHeader({ title, href, sub, action }: { title: string; href?: string; sub?: string; action?: React.ReactNode }) {
  return (
    <div className="mb-3 flex items-end justify-between gap-3">
      <div>
        <h2 className="text-lg font-bold tracking-tight sm:text-xl">{title}</h2>
        {sub && <p className="text-sm text-muted">{sub}</p>}
      </div>
      <div className="flex shrink-0 items-center gap-3">
        {href && (
          <Link href={href} className="inline-flex items-center text-sm font-semibold text-brand-700 hover:underline">
            See all <ChevronRight className="size-4" />
          </Link>
        )}
        {action}
      </div>
    </div>
  );
}

export function CategorySidebar({ categories }: { categories: Category[] }) {
  return (
    <nav aria-label="Categories" className="card overflow-hidden">
      <ul className="divide-y divide-line/70">
        {byListings(categories).map((c) => (
          <li key={c.id}>
            <Link href={`/c/${c.slug}`} className="group flex items-center gap-3 px-3 py-2.5 hover:bg-brand-50">
              <span className="grid size-9 shrink-0 place-items-center overflow-hidden rounded-lg bg-[#EEF0FF] p-0.5">
                {c.image_url ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img src={c.image_url} alt="" loading="lazy" className="size-full rounded-[6px] bg-white object-cover" />
                ) : (
                  <CategoryIcon name={c.icon} className="size-[18px] text-brand-700" />
                )}
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium group-hover:text-brand-800">{c.name}</span>
                <span className="block text-xs text-muted">{c.listing_count.toLocaleString()} {c.listing_count === 1 ? "ad" : "ads"}</span>
              </span>
              <ChevronRight className="size-4 text-muted" aria-hidden />
            </Link>
          </li>
        ))}
      </ul>
    </nav>
  );
}

export function CategoryTiles({ categories }: { categories: Category[] }) {
  // Mobile: a single row that auto-advances left and can also be swiped.
  return (
    <nav aria-label="Categories" className="-mx-3 px-3">
      <AutoCarousel label="Categories" arrows={false} slideClassName="basis-[86px]">
        {byListings(categories).map((c) => (
          <Link
            key={c.id}
            href={`/c/${c.slug}`}
            className="flex w-[86px] flex-col items-center gap-1.5 rounded-xl p-1 text-center"
          >
            <span className="grid size-16 shrink-0 place-items-center overflow-hidden rounded-2xl bg-[#EEF0FF] p-1.5">
              {c.image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img
                  src={c.image_url}
                  alt=""
                  loading="lazy"
                  className="size-full rounded-[10px] bg-white object-cover"
                />
              ) : (
                <CategoryIcon name={c.icon} className="size-6 text-brand-700" />
              )}
            </span>
            <span className="w-full truncate text-[11.5px] font-medium leading-tight">{c.name}</span>
          </Link>
        ))}
      </AutoCarousel>
    </nav>
  );
}

export function SellerTile({ s }: { s: SellerCard }) {
  return (
    <Link href={`/store/${s.slug}`} className="card flex w-56 shrink-0 items-center gap-3 p-3 transition hover:shadow-[var(--shadow-pop)] sm:w-auto">
      <span className={`grid size-12 shrink-0 place-items-center overflow-hidden rounded-full text-lg font-bold ${tintFor(s.slug)}`}>
        {s.logo_url ? (
          // eslint-disable-next-line @next/next/no-img-element
          <img src={s.logo_url} alt="" className="size-full object-cover" loading="lazy" />
        ) : (
          s.store_name[0]
        )}
      </span>
      <span className="min-w-0">
        <span className="block truncate text-sm font-semibold">{s.store_name}</span>
        <span className="flex items-center gap-1 text-xs text-muted">
          <Star className="size-3 fill-accent-500 text-accent-500" aria-hidden />
          {Number(s.rating_avg).toFixed(1)} · {s.completed_sales} sales
        </span>
        <span className="mt-1 flex gap-1">
          <VerifiedBadge level={s.verification_level} compact />
        </span>
      </span>
    </Link>
  );
}
