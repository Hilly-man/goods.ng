"use client";

import { Children, useEffect, useRef, useState } from "react";
import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";

const INTERVAL_MS = 3500;

/**
 * One-row carousel that auto-advances to the left and loops at the end.
 * Pauses on hover / touch / keyboard focus and respects prefers-reduced-motion.
 * `slideClassName` sets how many slides are visible per breakpoint (e.g. basis-[…]).
 */
export function AutoCarousel({ label, slideClassName, children, arrows = true }: {
  label: string; slideClassName: string; children: React.ReactNode; arrows?: boolean;
}) {
  const track = useRef<HTMLDivElement>(null);
  const [paused, setPaused] = useState(false);
  const [overflows, setOverflows] = useState(false);
  const resumeTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const slides = Children.toArray(children);

  useEffect(() => {
    const el = track.current;
    if (!el) return;
    const check = () => setOverflows(el.scrollWidth > el.clientWidth + 4);
    const ro = new ResizeObserver(check);
    ro.observe(el);
    return () => ro.disconnect();
  }, [slides.length]);

  const step = (dir: 1 | -1) => {
    const el = track.current;
    if (!el) return;
    const slide = el.querySelector<HTMLElement>("[data-slide]");
    const width = slide ? slide.offsetWidth + parseFloat(getComputedStyle(el).columnGap || "0") : el.clientWidth / 3;
    const atEnd = el.scrollLeft + el.clientWidth >= el.scrollWidth - 4;
    const atStart = el.scrollLeft <= 4;
    if (dir === 1 && atEnd) el.scrollTo({ left: 0, behavior: "smooth" });
    else if (dir === -1 && atStart) el.scrollTo({ left: el.scrollWidth, behavior: "smooth" });
    else el.scrollBy({ left: dir * width, behavior: "smooth" });
  };

  useEffect(() => {
    if (paused || !overflows) return;
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const id = setInterval(() => document.visibilityState === "visible" && step(1), INTERVAL_MS);
    return () => clearInterval(id);
  }, [paused, overflows]);

  // After a touch, resume auto-scrolling a few seconds later.
  const pauseBriefly = () => {
    setPaused(true);
    if (resumeTimer.current) clearTimeout(resumeTimer.current);
    resumeTimer.current = setTimeout(() => setPaused(false), 6000);
  };

  return (
    <div className="group/carousel relative" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)}
      onFocus={() => setPaused(true)} onBlur={() => setPaused(false)}>
      <div ref={track} role="region" aria-roledescription="carousel" aria-label={label} onTouchStart={pauseBriefly}
        className="scrollbar-none flex snap-x snap-mandatory gap-2 overflow-x-auto scroll-smooth pb-1 sm:gap-3">
        {slides.map((s, i) => (
          <div key={i} data-slide className={clsx("shrink-0 snap-start", slideClassName)}>{s}</div>
        ))}
      </div>
      {arrows && overflows && (
        <>
          <button type="button" onClick={() => step(-1)} aria-label={`Previous — ${label}`}
            className="absolute -left-4 top-1/2 hidden size-10 -translate-y-1/2 place-items-center rounded-full bg-white text-ink shadow-[var(--shadow-pop)] ring-1 ring-line opacity-0 transition group-hover/carousel:opacity-100 focus-visible:opacity-100 hover:text-brand-700 lg:grid">
            <ChevronLeft className="size-5" />
          </button>
          <button type="button" onClick={() => step(1)} aria-label={`Next — ${label}`}
            className="absolute -right-4 top-1/2 hidden size-10 -translate-y-1/2 place-items-center rounded-full bg-white text-ink shadow-[var(--shadow-pop)] ring-1 ring-line opacity-0 transition group-hover/carousel:opacity-100 focus-visible:opacity-100 hover:text-brand-700 lg:grid">
            <ChevronRight className="size-5" />
          </button>
        </>
      )}
    </div>
  );
}
