"use client";

import { byListings } from "@/lib/format";
import Link from "next/link";
import { useRef, useState } from "react";
import clsx from "clsx";
import { ChevronRight } from "lucide-react";
import type { Category } from "@/lib/types";
import { CategoryIcon, tintFor } from "./icons";

const ads = (n: number) => `${n.toLocaleString("en-US")} ${n === 1 ? "ad" : "ads"}`;

/**
 * Desktop category sidebar. Hovering (or focusing) a category opens a flyout to its right listing
 * its subcategories with live listing counts. A short close delay lets the pointer travel
 * diagonally from the sidebar into the flyout without it snapping shut.
 */
export function CategoryMenu({ categories }: { categories: Category[] }) {
  const [activeId, setActiveId] = useState<string | null>(null);
  const closeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const active = categories.find((c) => c.id === activeId) ?? null;

  const open = (id: string) => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    setActiveId(id);
  };
  const scheduleClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
    closeTimer.current = setTimeout(() => setActiveId(null), 150);
  };
  const cancelClose = () => {
    if (closeTimer.current) clearTimeout(closeTimer.current);
  };

  return (
    <div
      className="relative"
      onMouseLeave={scheduleClose}
      onMouseEnter={cancelClose}
      onKeyDown={(e) => e.key === "Escape" && setActiveId(null)}
    >
      <nav aria-label="Categories" className="card overflow-hidden">
        <ul className="divide-y divide-line/70">
          {byListings(categories).map((c) => {
            const isActive = c.id === activeId;
            return (
              <li key={c.id} onMouseEnter={() => open(c.id)}>
                <Link
                  href={`/c/${c.slug}`}
                  onFocus={() => open(c.id)}
                  aria-haspopup={c.children.length > 0 ? "true" : undefined}
                  aria-expanded={c.children.length > 0 ? isActive : undefined}
                  aria-controls={isActive ? "category-flyout" : undefined}
                  className={clsx("group flex items-center gap-3 px-3 py-2.5 transition-colors", isActive ? "bg-brand-50" : "hover:bg-brand-50")}
                >
                  <span className={`grid size-9 shrink-0 place-items-center rounded-lg ${tintFor(c.slug)}`}>
                    <CategoryIcon name={c.icon} className="size-[18px]" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className={clsx("block truncate text-sm font-medium", isActive && "text-brand-800")}>{c.name}</span>
                    <span className="block text-xs text-muted">{ads(c.listing_count)}</span>
                  </span>
                  <ChevronRight className={clsx("size-4 transition-transform", isActive ? "translate-x-0.5 text-brand-700" : "text-muted")} aria-hidden />
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>

      {active && active.children.length > 0 && (
        <div
          id="category-flyout"
          role="region"
          aria-label={`${active.name} subcategories`}
          className="card absolute left-full top-0 z-30 ml-2 max-h-full w-80 overflow-y-auto shadow-[var(--shadow-pop)]"
        >
          <Link href={`/c/${active.slug}`} className="flex items-center justify-between border-b border-line px-4 py-3 hover:bg-brand-50">
            <span>
              <span className="block text-sm font-bold">All {active.name}</span>
              <span className="text-xs text-muted">{ads(active.listing_count)}</span>
            </span>
            <ChevronRight className="size-4 text-brand-700" aria-hidden />
          </Link>
          <ul className="divide-y divide-line/70">
            {byListings(active.children).map((s) => (
              <li key={s.id}>
                <Link href={`/c/${s.slug}`} className="flex items-center gap-3 px-4 py-2.5 hover:bg-brand-50">
                  <span className={`grid size-8 shrink-0 place-items-center rounded-lg ${tintFor(active.slug)}`}>
                    <CategoryIcon name={active.icon} className="size-4" />
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-sm font-medium hover:text-brand-800">{s.name}</span>
                    <span className="block text-xs text-muted">{ads(s.listing_count)}</span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
