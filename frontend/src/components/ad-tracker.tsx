"use client";

import { useEffect, useRef } from "react";
import { trackAd, type AdPlacement } from "@/lib/ads";

/** Invisible helper placed inside a sponsored card: records an impression when the card is on screen, and clicks. */
export function AdTracker({ productId, placement }: { productId: string; placement: AdPlacement }) {
  const ref = useRef<HTMLSpanElement>(null);
  useEffect(() => {
    const card = ref.current?.closest("article");
    if (!card) return;
    const io = new IntersectionObserver((entries) => {
      if (entries.some((e) => e.isIntersecting)) { trackAd({ kind: "impression", placement, product_id: productId }); io.disconnect(); }
    }, { threshold: 0.5 });
    io.observe(card);
    const onClick = (e: Event) => {
      if ((e.target as HTMLElement).closest("a[href^='/item/']")) trackAd({ kind: "click", placement, product_id: productId });
    };
    card.addEventListener("click", onClick);
    return () => { io.disconnect(); card.removeEventListener("click", onClick); };
  }, [productId, placement]);
  return <span ref={ref} hidden />;
}

/** Small, neutral disclosure for promoted placements (like Jiji's "TOP"). Doesn't say who is Premium. */
export function SponsoredLabel({ className = "" }: { className?: string }) {
  return (
    <span className={`rounded bg-black/60 px-1.5 py-0.5 text-[10px] font-bold uppercase tracking-wide text-white backdrop-blur ${className}`}
      title="Promoted listing">Top</span>
  );
}
