"use client";

import { useEffect, useRef, useState } from "react";
import { ChevronLeft, ChevronRight } from "lucide-react";
import type { ProductCard as P } from "@/lib/types";
import { ProductCard } from "./product-card";

const INTERVAL_MS = 3500;

/**
 * Featured listings carousel — always cards (ignores the grid/list preference).
 * 3 per view on phones, 4 on tablets, 5 on desktop. Auto-advances to the left, loops at the end,
 * pauses on hover / touch / keyboard focus, and respects prefers-reduced-motion.
 */
export function FeaturedCarousel({ items }: { items: P[] }) {
  const track = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  const step = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const card = el.querySelector<HTMLElement>("[data-slide]");
    const width = card ? card.offsetWidth + parseFloat(getComputedStyle(el).columnGap || "0") : el.clientWidth / 3;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4;
    const atStart = el.scrollLeft <= 4;
    if (dir === 1 && atEnd) el.scrollTo({ left: 0, behavior: "smooth" });
    else if (dir === -1 && atStart) el.scrollTo({ left: el.scrollWidth, behavior: "smooth" });
    else el.scrollBy({ left: dir * width, behavior: "smooth" });
  };

  useEffect(() => {
    if (paused || items.length <= 3) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => document.visibilityState === "visible" && step(1), INTERVAL_MS);
    return () => clearInterval(id);
  }, [paused, items.length]);

  // After a touch, resume auto-scrolling a few seconds later.
  const pauseBriefly = () => {
    setPaused(true);
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => setPaused(false), 6000);
  };

  return (
    <div className="group/carousel relative" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div ref={track} role="region" aria-roledescription="carousel" aria-label="Featured listings"
        onTouchStart={pauseBriefly}
        className="scrollbar-none flex snap-x snap-mandatory gap-2 overflow-x-auto scroll-smooth pb-1 sm:gap-3">
        {items.map((p, i) => (
          <div key={p.id} data-slide
            className="shrink-0 basis-[calc((100%-1rem)/3)] snap-start sm:basis-[calc((100%-2.25rem)/4)] lg:basis-[calc((100%-3rem)/5)]">
            <ProductCard p={p} eager={i < 5} compact />
          </div>
        ))}
      </div>
      {items.length > 5 && (
        <>
          <button type="button" onClick={() => step(-1)} aria-label="Previous featured listings"
            className="absolute -left-4 top-[30%] hidden size-10 place-items-center rounded-full bg-white text-ink shadow-[var(--shadow-pop)] ring-1 ring-line transition hover:text-brand-700 lg:grid">
            <ChevronLeft className="size-5" />
          </button>
          <button type="button" onClick={() => step(1)} aria-label="Next featured listings"
            className="absolute -right-4 top-[30%] hidden size-10 place-items-center rounded-full bg-white text-ink shadow-[var(--shadow-pop)] ring-1 ring-line transition hover:text-brand-700 lg:grid">
            <ChevronRight className="size-5" />
          </button>
        </>
      )}
    </div>
  );
}
